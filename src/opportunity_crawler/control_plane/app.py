from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
import json
import uuid

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel

from opportunity_crawler.agent.runtime.collection_runner import CollectionRunner
from opportunity_crawler.control_plane.routes.api.errors import ApiError, api_error
from opportunity_crawler.control_plane.services.auth_service import AuthService, AuthenticatedUser
from opportunity_crawler.control_plane.services.collection_run_service import CollectionRunService
from opportunity_crawler.control_plane.services.customer_service import CustomerService
from opportunity_crawler.control_plane.services.goal_service import GoalService
from opportunity_crawler.control_plane.services.normalization_service import CandidateCreationService, ManualCandidateInput
from opportunity_crawler.control_plane.services.permission_service import PermissionService
from opportunity_crawler.control_plane.services.review_service import ReviewService
from opportunity_crawler.control_plane.services.runtime_registry import RuntimeRegistry
from opportunity_crawler.control_plane.workers.notification_worker import NotificationWorker
from opportunity_crawler.shared.contracts.agent_protocol import (
    CollectionCommandMessage,
    CollectionEventKind,
    CollectionEventMessage,
    ControlPlaneCommandKind,
    parse_agent_message,
)
from opportunity_crawler.shared.db.base import connect_sqlite
from opportunity_crawler.shared.domain.audit import mask_audit_payload
from opportunity_crawler.shared.domain.rules import RuleValidationError, validate_advanced_rule_config


class LoginRequest(BaseModel):
    username: str
    password: str


class BasicRuleUpdate(BaseModel):
    frequency: str | None = None
    digest_enabled: bool | None = None
    digest_score_threshold: int | None = None
    regions: list[str] | None = None
    industry_keywords: list[str] | None = None
    demand_keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None


class TrialRunRequest(BaseModel):
    max_items: int = 5


class StartCollectionRunRequest(BaseModel):
    agent_id: str | None = None


class ManualImportRequest(BaseModel):
    source_id: int
    title: str
    url: str | None = None
    body: str
    organization_name: str | None = None
    region: str | None = None
    industry: str | None = None
    project_stage: str | None = None
    budget_amount: float | None = None


class ReviewRequest(BaseModel):
    review_status: str


class FollowUpRequest(BaseModel):
    follow_up_status: str
    note: str | None = None


class DigestRequest(BaseModel):
    simulate_failure: bool = False


def create_app(database_path: str | Path) -> FastAPI:
    app = FastAPI(title="Opportunity Crawler Control Plane")
    app.state.database_path = Path(database_path)
    app.state.auth_service = AuthService(app.state.database_path)
    app.state.permission_service = PermissionService()
    app.state.runtime_registry = RuntimeRegistry(app.state.database_path)
    app.state.trial_browser_runtime = None

    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> Response:
        return api_error(
            exc.code,
            exc.message,
            status_code=exc.status_code,
            details=exc.details,
        )

    @app.post("/api/auth/login")
    async def login(payload: LoginRequest) -> dict[str, Any]:
        result = app.state.auth_service.authenticate(payload.username, payload.password)
        if result is None:
            raise ApiError("invalid_credentials", "Invalid username or password", status_code=401)
        token, user = result
        return {"access_token": token, "token_type": "bearer", "user": user.as_dict()}

    @app.get("/api/auth/me")
    async def current_user(request: Request) -> dict[str, Any]:
        user = _require_user(request)
        return {"user": user.as_dict()}

    @app.get("/api/sources")
    async def list_sources(request: Request) -> dict[str, Any]:
        _require_user(request)
        with connect_sqlite(app.state.database_path) as connection:
            rows = connection.execute(
                """
                SELECT id, name, category, home_url, priority, enabled, adapter_mode,
                       login_mode, login_status, health_status, active_rule_version_id,
                       last_success_at, last_failure_reason
                FROM sources
                ORDER BY priority, id
                """,
            ).fetchall()
        return {"items": [dict(row) for row in rows]}

    @app.get("/api/dashboard/summary")
    async def dashboard_summary(request: Request) -> dict[str, Any]:
        _require_user(request)
        with connect_sqlite(app.state.database_path) as connection:
            source_total = int(connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0])
            healthy_sources = int(
                connection.execute("SELECT COUNT(*) FROM sources WHERE health_status = 'healthy'").fetchone()[0]
            )
            failed_sources = int(
                connection.execute("SELECT COUNT(*) FROM sources WHERE health_status = 'failed'").fetchone()[0]
            )
            login_required_sources = int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM sources
                    WHERE login_status NOT IN ('not_required', 'logged_in')
                    """,
                ).fetchone()[0]
            )
            pending_opportunities = int(
                connection.execute(
                    "SELECT COUNT(*) FROM opportunity_candidates WHERE review_status = 'pending'",
                ).fetchone()[0]
            )
            accepted_opportunities = int(
                connection.execute(
                    "SELECT COUNT(*) FROM opportunity_candidates WHERE review_status = 'accepted'",
                ).fetchone()[0]
            )
            high_score_opportunities = int(
                connection.execute(
                    "SELECT COUNT(*) FROM opportunity_candidates WHERE score >= 70",
                ).fetchone()[0]
            )
            failed_runs = int(
                connection.execute("SELECT COUNT(*) FROM collection_runs WHERE status = 'failed'").fetchone()[0]
            )
            running_runs = int(
                connection.execute("SELECT COUNT(*) FROM collection_runs WHERE status = 'running'").fetchone()[0]
            )
            online_agents = int(
                connection.execute("SELECT COUNT(*) FROM agent_instances WHERE status = 'online'").fetchone()[0]
            )
        return {
            "sources": {
                "total": source_total,
                "healthy": healthy_sources,
                "failed": failed_sources,
                "login_required": login_required_sources,
            },
            "opportunities": {
                "pending": pending_opportunities,
                "accepted": accepted_opportunities,
                "high_score": high_score_opportunities,
            },
            "runs": {"running": running_runs, "failed": failed_runs},
            "agents": {"online": online_agents},
        }

    @app.get("/api/sources/{source_id}")
    async def source_detail(source_id: int, request: Request) -> dict[str, Any]:
        _require_user(request)
        with connect_sqlite(app.state.database_path) as connection:
            source = connection.execute(
                """
                SELECT id, name, category, home_url, priority, enabled, adapter_mode,
                       login_mode, login_status, health_status, active_rule_version_id,
                       maintenance_owner, last_success_at, last_failure_at, last_failure_reason,
                       created_at, updated_at
                FROM sources
                WHERE id = ?
                """,
                (source_id,),
            ).fetchone()
            if source is None:
                raise ApiError("not_found", "Source not found", status_code=404)
            basic_rules = connection.execute(
                "SELECT * FROM source_basic_rules WHERE source_id = ?",
                (source_id,),
            ).fetchone()
            active_rule = connection.execute(
                """
                SELECT *
                FROM source_advanced_rule_versions
                WHERE source_id = ? AND status = 'active'
                ORDER BY version DESC
                LIMIT 1
                """,
                (source_id,),
            ).fetchone()
        return {
            "source": dict(source),
            "basic_rules": _source_basic_rules_payload(basic_rules),
            "active_rule": _advanced_rule_payload(active_rule) if active_rule is not None else None,
        }

    @app.get("/api/sources/{source_id}/advanced-rules")
    async def list_advanced_rules(source_id: int, request: Request) -> dict[str, Any]:
        _require_user(request)
        with connect_sqlite(app.state.database_path) as connection:
            source = connection.execute("SELECT id FROM sources WHERE id = ?", (source_id,)).fetchone()
            if source is None:
                raise ApiError("not_found", "Source not found", status_code=404)
            rows = connection.execute(
                """
                SELECT *
                FROM source_advanced_rule_versions
                WHERE source_id = ?
                ORDER BY version DESC
                """,
                (source_id,),
            ).fetchall()
        return {"items": [_advanced_rule_payload(row) for row in rows]}

    @app.patch("/api/sources/{source_id}/basic-rules")
    async def update_basic_rules(source_id: int, payload: BasicRuleUpdate, request: Request) -> dict[str, Any]:
        user = _require_permission(request, "source.basic_rules:update")
        updates: dict[str, Any] = {}
        if payload.frequency is not None:
            updates["frequency"] = payload.frequency
        if payload.digest_enabled is not None:
            updates["digest_enabled"] = 1 if payload.digest_enabled else 0
        if payload.digest_score_threshold is not None:
            updates["digest_score_threshold"] = payload.digest_score_threshold
        if payload.regions is not None:
            updates["regions_json"] = _json(payload.regions)
        if payload.industry_keywords is not None:
            updates["industry_keywords_json"] = _json(payload.industry_keywords)
        if payload.demand_keywords is not None:
            updates["demand_keywords_json"] = _json(payload.demand_keywords)
        if payload.exclude_keywords is not None:
            updates["exclude_keywords_json"] = _json(payload.exclude_keywords)
        if not updates:
            raise ApiError("validation_error", "No fields to update", status_code=422)

        with connect_sqlite(app.state.database_path) as connection:
            assignments = ", ".join(f"{field} = ?" for field in updates)
            connection.execute(
                f"""
                UPDATE source_basic_rules
                SET {assignments}, updated_by = ?, updated_at = CURRENT_TIMESTAMP
                WHERE source_id = ?
                """,
                (*updates.values(), user.username, source_id),
            )
            _write_audit(
                connection,
                actor_id=user.id,
                action="source.basic_rules.update",
                resource_type="source",
                resource_id=str(source_id),
                after=updates,
            )
            connection.commit()
            row = connection.execute(
                "SELECT * FROM source_basic_rules WHERE source_id = ?",
                (source_id,),
            ).fetchone()
        return dict(row)

    @app.post("/api/sources/{source_id}/advanced-rules", status_code=201)
    async def create_advanced_rule(source_id: int, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        user = _require_permission(request, "source.advanced_rules:update")
        try:
            config = validate_advanced_rule_config(payload)
        except RuleValidationError as exc:
            raise ApiError("validation_error", "Invalid advanced rule config", status_code=422, details=exc.errors) from exc

        with connect_sqlite(app.state.database_path) as connection:
            version = int(
                connection.execute(
                    "SELECT COALESCE(MAX(version), 0) + 1 FROM source_advanced_rule_versions WHERE source_id = ?",
                    (source_id,),
                ).fetchone()[0]
            )
            connection.execute(
                """
                INSERT INTO source_advanced_rule_versions (
                    source_id, version, status, adapter_mode, entry_url, login_mode,
                    selectors_json, pagination_policy_json, normalization_mapping_json,
                    attachment_policy_json, risk_patterns_json, rate_limit_policy_json,
                    retry_policy_json, created_by
                )
                VALUES (?, ?, 'draft', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    version,
                    config.adapter_mode,
                    config.entry_url,
                    config.login_mode,
                    _json(config.selectors),
                    _json(config.pagination_policy),
                    _json(config.normalization_mapping),
                    _json(config.attachment_policy),
                    _json(config.risk_patterns),
                    _json(config.rate_limit_policy),
                    _json(config.retry_policy),
                    user.username,
                ),
            )
            _write_audit(
                connection,
                actor_id=user.id,
                action="source.advanced_rule.create",
                resource_type="source",
                resource_id=str(source_id),
                after={"version": version, "status": "draft"},
            )
            connection.commit()
        return {"source_id": source_id, "version": version, "status": "draft"}

    @app.post("/api/sources/{source_id}/advanced-rules/{version}/trial-run")
    async def trial_run_rule(source_id: int, version: int, payload: TrialRunRequest, request: Request) -> dict[str, Any]:
        _require_permission(request, "source.advanced_rules:update")
        with connect_sqlite(app.state.database_path) as connection:
            row = _require_rule_version(connection, source_id, version)
            rule = _advanced_rule_payload(row)

        command = CollectionCommandMessage(
            command=ControlPlaneCommandKind.TRIAL_RUN_ADVANCED_RULE,
            command_id=f"trial-cmd-{uuid.uuid4()}",
            run_id=f"trial-run-{uuid.uuid4()}",
            source_id=source_id,
            rule_version=version,
            adapter_mode=str(rule["adapter_mode"]),
            login_mode=str(rule["login_mode"]),
            draft_rule_payload=_trial_rule_payload(rule),
            max_items=payload.max_items,
        )
        result = await CollectionRunner(browser_runtime=app.state.trial_browser_runtime).trial_run_advanced_rule(command)
        preview_rows = (
            result.get("rows", [])
            if result.get("event_kind") in {CollectionEventKind.TRIAL_RUN_COMPLETED, CollectionEventKind.TRIAL_RUN_COMPLETED.value}
            else []
        )
        diagnostic_snapshot = dict(result.get("diagnostic_snapshot") or {})
        if result.get("failure_kind"):
            diagnostic_snapshot["failure_kind"] = result["failure_kind"]
        if result.get("detail"):
            diagnostic_snapshot["detail"] = result["detail"]

        trial_snapshot = {
            "event_kind": _event_kind_value(result.get("event_kind")),
            "preview_rows": preview_rows,
            "diagnostic_snapshot": diagnostic_snapshot,
            "item_count": len(preview_rows),
            "page_count": int(result.get("page_count") or 0),
        }
        with connect_sqlite(app.state.database_path) as connection:
            connection.execute(
                """
                UPDATE source_advanced_rule_versions
                SET trial_run_snapshot_json = ?
                WHERE source_id = ? AND version = ?
                """,
                (_json(trial_snapshot), source_id, version),
            )
            connection.commit()

        return {
            "source_id": source_id,
            "version": version,
            "max_items": payload.max_items,
            "preview_rows": preview_rows,
            "diagnostic_snapshot": diagnostic_snapshot,
        }

    @app.post("/api/sources/{source_id}/advanced-rules/{version}/activate")
    async def activate_rule(source_id: int, version: int, request: Request) -> dict[str, Any]:
        user = _require_permission(request, "source.advanced_rules:update")
        return _activate_rule(app.state.database_path, source_id, version, user, action="source.advanced_rule.activate")

    @app.post("/api/sources/{source_id}/advanced-rules/{version}/rollback")
    async def rollback_rule(source_id: int, version: int, request: Request) -> dict[str, Any]:
        user = _require_permission(request, "source.advanced_rules:update")
        return _activate_rule(app.state.database_path, source_id, version, user, action="source.advanced_rule.rollback")

    @app.post("/api/opportunities/manual-import", status_code=201)
    async def manual_import(payload: ManualImportRequest, request: Request) -> dict[str, Any]:
        user = _require_permission(request, "opportunities:write")
        service = CandidateCreationService(app.state.database_path)
        try:
            row = service.create_from_manual_import(
                ManualCandidateInput(
                    source_id=payload.source_id,
                    title=payload.title,
                    url=payload.url,
                    body=payload.body,
                    organization_name=payload.organization_name,
                    region=payload.region,
                    industry=payload.industry,
                    project_stage=payload.project_stage,
                    budget_amount=payload.budget_amount,
                )
            )
        except KeyError as exc:
            raise ApiError("not_found", "Source not found", status_code=404) from exc

        with connect_sqlite(app.state.database_path) as connection:
            _write_audit(
                connection,
                actor_id=user.id,
                action="opportunity.manual_import",
                resource_type="opportunity_candidate",
                resource_id=str(row["id"]),
                after={"title": payload.title, "source_id": payload.source_id},
            )
            connection.commit()
        return row

    @app.get("/api/opportunities")
    async def list_opportunities(
        request: Request,
        review_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        _require_user(request)
        normalized_limit = max(1, min(limit, 200))
        normalized_offset = max(0, offset)
        filters: list[str] = []
        params: list[Any] = []
        if review_status:
            filters.append("oc.review_status = ?")
            params.append(review_status)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        with connect_sqlite(app.state.database_path) as connection:
            rows = connection.execute(
                f"""
                SELECT oc.*, s.name AS source_name, s.priority AS source_priority
                FROM opportunity_candidates oc
                JOIN sources s ON s.id = oc.source_id
                {where_clause}
                ORDER BY oc.score DESC, oc.id DESC
                LIMIT ? OFFSET ?
                """,
                (*params, normalized_limit, normalized_offset),
            ).fetchall()
            total = int(
                connection.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM opportunity_candidates oc
                    {where_clause}
                    """,
                    params,
                ).fetchone()[0]
            )
        return {"items": [dict(row) for row in rows], "total": total, "limit": normalized_limit, "offset": normalized_offset}

    @app.get("/api/opportunities/{candidate_id}")
    async def opportunity_detail(candidate_id: int, request: Request) -> dict[str, Any]:
        _require_user(request)
        with connect_sqlite(app.state.database_path) as connection:
            candidate = connection.execute(
                "SELECT * FROM opportunity_candidates WHERE id = ?",
                (candidate_id,),
            ).fetchone()
            if candidate is None:
                raise ApiError("not_found", "Opportunity candidate not found", status_code=404)
            source = connection.execute(
                """
                SELECT id, name, category, home_url, priority, adapter_mode, login_mode,
                       login_status, health_status
                FROM sources
                WHERE id = ?
                """,
                (candidate["source_id"],),
            ).fetchone()
            evidence = connection.execute(
                "SELECT * FROM raw_evidence_items WHERE id = ?",
                (candidate["evidence_id"],),
            ).fetchone()
            analysis = connection.execute(
                "SELECT * FROM candidate_analysis WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()
        return {
            "candidate": dict(candidate),
            "source": dict(source) if source is not None else None,
            "evidence": _evidence_payload(evidence) if evidence is not None else None,
            "analysis": _analysis_payload(analysis) if analysis is not None else None,
        }

    @app.post("/api/opportunities/{candidate_id}/review")
    async def review_candidate(candidate_id: int, payload: ReviewRequest, request: Request) -> dict[str, Any]:
        user = _require_permission(request, "opportunities:review")
        service = ReviewService(app.state.database_path)
        try:
            row = service.update_review_status(candidate_id, payload.review_status)
        except ValueError as exc:
            raise ApiError("validation_error", "Invalid review status", status_code=422)
        except KeyError as exc:
            raise ApiError("not_found", "Candidate not found", status_code=404) from exc
        with connect_sqlite(app.state.database_path) as connection:
            _write_audit(
                connection,
                actor_id=user.id,
                action="opportunity.review",
                resource_type="opportunity_candidate",
                resource_id=str(candidate_id),
                after={"review_status": payload.review_status},
            )
            connection.commit()
        return row

    @app.post("/api/opportunities/{candidate_id}/follow-up")
    async def update_follow_up(candidate_id: int, payload: FollowUpRequest, request: Request) -> dict[str, Any]:
        user = _require_permission(request, "opportunities:review")
        service = ReviewService(app.state.database_path)
        try:
            row = service.update_follow_up_status(
                candidate_id,
                follow_up_status=payload.follow_up_status,
                note=payload.note,
                actor_id=user.id,
            )
        except ValueError as exc:
            raise ApiError("validation_error", "Invalid follow-up status", status_code=422) from exc
        except KeyError as exc:
            raise ApiError("not_found", "Candidate not found", status_code=404) from exc
        with connect_sqlite(app.state.database_path) as connection:
            _write_audit(
                connection,
                actor_id=user.id,
                action="opportunity.follow_up",
                resource_type="opportunity_candidate",
                resource_id=str(candidate_id),
                after={"follow_up_status": payload.follow_up_status},
            )
            connection.commit()
        return row

    @app.get("/api/customers/{customer_name}/history")
    async def customer_history(customer_name: str, request: Request) -> dict[str, Any]:
        _require_permission(request, "opportunities:review")
        return CustomerService(app.state.database_path).history_for_customer(customer_name)

    @app.get("/api/customers")
    async def list_customers(request: Request, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        _require_user(request)
        normalized_limit = max(1, min(limit, 200))
        normalized_offset = max(0, offset)
        with connect_sqlite(app.state.database_path) as connection:
            rows = connection.execute(
                """
                SELECT c.*,
                       COUNT(DISTINCT oc.id) AS opportunity_count,
                       MAX(ca.occurred_at) AS last_activity_at
                FROM customers c
                LEFT JOIN opportunity_candidates oc ON oc.organization_name = c.name
                LEFT JOIN customer_activities ca ON ca.customer_id = c.id
                GROUP BY c.id
                ORDER BY c.id DESC
                LIMIT ? OFFSET ?
                """,
                (normalized_limit, normalized_offset),
            ).fetchall()
            total = int(connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0])
        return {"items": [dict(row) for row in rows], "total": total, "limit": normalized_limit, "offset": normalized_offset}

    @app.get("/api/goals/weekly-progress")
    async def weekly_progress(week_start: str, request: Request) -> dict[str, Any]:
        _require_permission(request, "goals:read")
        return GoalService(app.state.database_path).weekly_progress(week_start=week_start)

    @app.get("/api/collection-runs")
    async def list_collection_runs(request: Request, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        _require_user(request)
        normalized_limit = max(1, min(limit, 200))
        normalized_offset = max(0, offset)
        with connect_sqlite(app.state.database_path) as connection:
            rows = connection.execute(
                """
                SELECT cr.*, s.name AS source_name
                FROM collection_runs cr
                JOIN sources s ON s.id = cr.source_id
                ORDER BY COALESCE(cr.started_at, cr.scheduled_at, cr.finished_at, cr.run_id) DESC
                LIMIT ? OFFSET ?
                """,
                (normalized_limit, normalized_offset),
            ).fetchall()
            total = int(connection.execute("SELECT COUNT(*) FROM collection_runs").fetchone()[0])
        return {
            "items": [_collection_run_payload(row) for row in rows],
            "total": total,
            "limit": normalized_limit,
            "offset": normalized_offset,
        }

    @app.post("/api/sources/{source_id}/collection-runs", status_code=201)
    async def start_collection_run(
        source_id: int,
        request: Request,
        payload: StartCollectionRunRequest | None = None,
    ) -> dict[str, Any]:
        _require_permission(request, "collection_runs:manage")
        try:
            agent = app.state.runtime_registry.choose_agent(payload.agent_id if payload else None)
        except KeyError as exc:
            raise ApiError("agent_unavailable", "No online Agent is available for collection", status_code=409) from exc

        service = CollectionRunService(app.state.database_path)
        try:
            result = service.start_run(source_id=source_id, agent_id=str(agent["agent_id"]))
        except KeyError as exc:
            raise ApiError("not_found", "Source not found", status_code=404) from exc
        except ValueError as exc:
            raise ApiError("validation_error", str(exc), status_code=422) from exc

        app.state.runtime_registry.dispatch_command(str(agent["agent_id"]), result["command"])
        return result

    @app.get("/api/collection-runs/{run_id}/evidence")
    async def collection_run_evidence(run_id: str, request: Request, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        _require_user(request)
        normalized_limit = max(1, min(limit, 500))
        normalized_offset = max(0, offset)
        with connect_sqlite(app.state.database_path) as connection:
            run = connection.execute(
                "SELECT run_id FROM collection_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if run is None:
                raise ApiError("not_found", "Collection run not found", status_code=404)
            rows = connection.execute(
                """
                SELECT *
                FROM raw_evidence_items
                WHERE run_id = ?
                ORDER BY id
                LIMIT ? OFFSET ?
                """,
                (run_id, normalized_limit, normalized_offset),
            ).fetchall()
            total = int(
                connection.execute(
                    "SELECT COUNT(*) FROM raw_evidence_items WHERE run_id = ?",
                    (run_id,),
                ).fetchone()[0]
            )
        return {
            "items": [_evidence_payload(row) for row in rows],
            "total": total,
            "limit": normalized_limit,
            "offset": normalized_offset,
        }

    @app.get("/api/agents")
    async def list_agents(request: Request) -> dict[str, Any]:
        _require_user(request)
        with connect_sqlite(app.state.database_path) as connection:
            rows = connection.execute(
                """
                SELECT ai.agent_id, ai.host_id, ah.hostname, ah.platform, ah.app_version,
                       ai.status, ai.capacity, ai.active_sessions, ai.last_heartbeat_at,
                       ah.last_seen_at
                FROM agent_instances ai
                LEFT JOIN agent_hosts ah ON ah.host_id = ai.host_id
                ORDER BY ai.agent_id
                """,
            ).fetchall()
        return {"items": [dict(row) for row in rows]}

    @app.post("/api/notifications/dingtalk/digest")
    async def send_dingtalk_digest(payload: DigestRequest, request: Request) -> dict[str, Any]:
        _require_permission(request, "notifications:read")
        return NotificationWorker(app.state.database_path).send_daily_digest(simulate_failure=payload.simulate_failure)

    @app.get("/api/notifications/logs")
    async def list_notification_logs(request: Request, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        _require_user(request)
        normalized_limit = max(1, min(limit, 200))
        normalized_offset = max(0, offset)
        with connect_sqlite(app.state.database_path) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM notification_logs
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (normalized_limit, normalized_offset),
            ).fetchall()
            total = int(connection.execute("SELECT COUNT(*) FROM notification_logs").fetchone()[0])
        return {
            "items": [_notification_log_payload(row) for row in rows],
            "total": total,
            "limit": normalized_limit,
            "offset": normalized_offset,
        }

    @app.get("/api/audit-logs")
    async def list_audit_logs(request: Request, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        _require_user(request)
        normalized_limit = max(1, min(limit, 200))
        normalized_offset = max(0, offset)
        with connect_sqlite(app.state.database_path) as connection:
            rows = connection.execute(
                """
                SELECT al.*, u.username AS actor_username
                FROM audit_logs al
                LEFT JOIN users u ON u.id = al.actor_id
                ORDER BY al.id DESC
                LIMIT ? OFFSET ?
                """,
                (normalized_limit, normalized_offset),
            ).fetchall()
            total = int(connection.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0])
        return {
            "items": [_audit_log_payload(row) for row in rows],
            "total": total,
            "limit": normalized_limit,
            "offset": normalized_offset,
        }

    @app.websocket("/api/agents/ws")
    async def agent_websocket(websocket: WebSocket) -> None:
        await websocket.accept()
        agent_id: str | None = None
        protocol_mode = "legacy"
        try:
            while True:
                if agent_id is not None:
                    await _drain_agent_commands(websocket, app.state.runtime_registry, agent_id)
                try:
                    message = await asyncio.wait_for(websocket.receive_json(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue

                message_type = message.get("message_type") or message.get("type")
                if message_type == "register":
                    protocol_mode = "protocol" if message.get("message_type") == "register" else "legacy"
                    presence = app.state.runtime_registry.register(message)
                    agent_id = presence["agent_id"]
                    if protocol_mode == "protocol":
                        await websocket.send_json(
                            {
                                "message_type": "registered",
                                "agent_id": presence["agent_id"],
                                "host_id": presence["host_id"],
                            }
                        )
                    else:
                        await websocket.send_json({"type": "registered", "agent_id": presence["agent_id"]})
                elif message_type == "heartbeat":
                    presence = app.state.runtime_registry.heartbeat(str(message["agent_id"]))
                    if protocol_mode == "protocol":
                        await websocket.send_json({"message_type": "heartbeat_ack", "agent_id": presence["agent_id"]})
                    else:
                        await websocket.send_json({"type": "heartbeat_ack", "agent_id": presence["agent_id"]})
                elif message_type == "collection_event":
                    try:
                        parsed = parse_agent_message(message)
                    except ValueError as exc:
                        await _send_agent_error(websocket, protocol_mode, "invalid_message", str(exc))
                        continue
                    if not isinstance(parsed, CollectionEventMessage):
                        await _send_agent_error(websocket, protocol_mode, "invalid_message", "Expected collection_event")
                        continue
                    try:
                        CollectionRunService(app.state.database_path).record_event(agent_id=agent_id, event=parsed)
                    except KeyError:
                        await _send_agent_error(websocket, protocol_mode, "not_found", "Collection run not found")
                        continue
                    await websocket.send_json(
                        {
                            "message_type": "collection_event_ack",
                            "event_kind": parsed.event_kind.value,
                            "run_id": parsed.run_id,
                        }
                    )
                else:
                    await _send_agent_error(websocket, protocol_mode, "unsupported_message", "Unsupported Agent message")
        except WebSocketDisconnect:
            return

    @app.get("/api/events")
    async def events(request: Request) -> Response:
        _require_user(request)
        body = f"event: snapshot\ndata: {_json(_runtime_snapshot(app))}\n\n"
        return Response(content=body, media_type="text/event-stream")

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        with connect_sqlite(app.state.database_path) as connection:
            migration_count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
        return {
            "database": {"ok": True},
            "migrations": {"ok": migration_count > 0},
            "agents": {"online": app.state.runtime_registry.online_count()},
            "browser": _browser_health(app),
        }

    return app


async def _drain_agent_commands(websocket: WebSocket, registry: RuntimeRegistry, agent_id: str) -> None:
    for command in registry.pop_commands(agent_id):
        await websocket.send_json(command)


async def _send_agent_error(websocket: WebSocket, protocol_mode: str, code: str, message: str) -> None:
    if protocol_mode == "protocol":
        await websocket.send_json({"message_type": "error", "code": code, "message": message})
    else:
        await websocket.send_json({"type": "error", "code": code, "message": message})


def _require_user(request: Request) -> AuthenticatedUser:
    authorization = request.headers.get("authorization", "")
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise ApiError("not_authenticated", "Authentication required", status_code=401)
    token = authorization[len(prefix) :]
    user = request.app.state.auth_service.user_for_token(token)
    if user is None:
        raise ApiError("not_authenticated", "Authentication required", status_code=401)
    return user


def _require_permission(request: Request, permission: str) -> AuthenticatedUser:
    user = _require_user(request)
    if not request.app.state.permission_service.has_permission(user.roles, permission):
        raise ApiError("permission_denied", "Permission denied", status_code=403)
    return user


def _require_rule_version(connection: Any, source_id: int, version: int) -> Any:
    row = connection.execute(
        """
        SELECT * FROM source_advanced_rule_versions
        WHERE source_id = ? AND version = ?
        """,
        (source_id, version),
    ).fetchone()
    if row is None:
        raise ApiError("not_found", "Advanced rule version not found", status_code=404)
    return row


def _activate_rule(
    database_path: Path,
    source_id: int,
    version: int,
    user: AuthenticatedUser,
    *,
    action: str,
) -> dict[str, Any]:
    with connect_sqlite(database_path) as connection:
        row = _require_rule_version(connection, source_id, version)
        connection.execute(
            """
            UPDATE source_advanced_rule_versions
            SET status = 'archived'
            WHERE source_id = ? AND status = 'active'
            """,
            (source_id,),
        )
        connection.execute(
            """
            UPDATE source_advanced_rule_versions
            SET status = 'active', activated_at = CURRENT_TIMESTAMP
            WHERE source_id = ? AND version = ?
            """,
            (source_id, version),
        )
        connection.execute(
            """
            UPDATE sources
            SET active_rule_version_id = (
                SELECT id FROM source_advanced_rule_versions
                WHERE source_id = ? AND version = ?
            )
            WHERE id = ?
            """,
            (source_id, version, source_id),
        )
        _write_audit(
            connection,
            actor_id=user.id,
            action=action,
            resource_type="source",
            resource_id=str(source_id),
            after={"version": version, "status": "active"},
        )
        connection.commit()
    _ = row
    return {"source_id": source_id, "version": version, "status": "active"}


def _write_audit(
    connection: Any,
    *,
    actor_id: int,
    action: str,
    resource_type: str,
    resource_id: str,
    after: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO audit_logs (actor_id, action, resource_type, resource_id, after_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (actor_id, action, resource_type, resource_id, _json(mask_audit_payload(after))),
    )


def _source_basic_rules_payload(row: Any | None) -> dict[str, Any] | None:
    if row is None:
        return None
    payload = dict(row)
    for field in ("regions_json", "industry_keywords_json", "demand_keywords_json", "exclude_keywords_json"):
        output_field = field.removesuffix("_json")
        payload[output_field] = _read_json(payload.pop(field), [])
    payload["digest_enabled"] = bool(payload["digest_enabled"])
    return payload


def _advanced_rule_payload(row: Any) -> dict[str, Any]:
    payload = dict(row)
    for field in (
        "selectors_json",
        "pagination_policy_json",
        "normalization_mapping_json",
        "attachment_policy_json",
        "risk_patterns_json",
        "rate_limit_policy_json",
        "retry_policy_json",
    ):
        output_field = field.removesuffix("_json")
        payload[output_field] = _read_json(payload.pop(field), {})
    payload["trial_run_snapshot"] = _read_json(payload.pop("trial_run_snapshot_json"), None)
    return payload


def _trial_rule_payload(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "entry_url": rule["entry_url"],
        "selectors": rule.get("selectors") or {},
        "pagination_policy": rule.get("pagination_policy") or {},
        "normalization_mapping": rule.get("normalization_mapping") or {},
        "attachment_policy": rule.get("attachment_policy") or {},
        "risk_patterns": rule.get("risk_patterns") or {},
        "rate_limit_policy": rule.get("rate_limit_policy") or {},
        "retry_policy": rule.get("retry_policy") or {},
    }


def _event_kind_value(value: Any) -> str | None:
    return value.value if hasattr(value, "value") else value


def _runtime_snapshot(app: FastAPI) -> dict[str, Any]:
    with connect_sqlite(app.state.database_path) as connection:
        run_rows = connection.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM collection_runs
            GROUP BY status
            """
        ).fetchall()
    return {
        "type": "snapshot",
        "agents_online": app.state.runtime_registry.online_count(),
        "runs": {str(row["status"]): int(row["count"]) for row in run_rows},
    }


def _browser_health(app: FastAPI) -> dict[str, Any]:
    trial_runtime = getattr(app.state, "trial_browser_runtime", None)
    has_trial_runtime = callable(getattr(trial_runtime, "fetch_html", None)) or callable(
        getattr(trial_runtime, "open_url", None)
    )
    if has_trial_runtime:
        return {"ok": True, "detail": "trial browser runtime configured"}
    if app.state.runtime_registry.online_count() > 0:
        return {"ok": True, "detail": "Agent online; browser execution delegated to Agent"}
    return {"ok": False, "detail": "no Agent online and no trial browser runtime configured"}


def _evidence_payload(row: Any) -> dict[str, Any]:
    payload = dict(row)
    payload["attachments"] = _read_json(payload.pop("attachments_json"), [])
    return payload


def _analysis_payload(row: Any) -> dict[str, Any]:
    payload = dict(row)
    return {
        "candidate_id": payload["candidate_id"],
        "extracted_facts": _read_json(payload["extracted_facts_json"], {}),
        "inferred_analysis": _read_json(payload["inferred_analysis_json"], {}),
        "scoring_reasons": _read_json(payload["scoring_reasons_json"], {}),
        "outreach": _read_json(payload["outreach_json"], {}),
        "provider_metadata": _read_json(payload["provider_metadata_json"], {}),
        "updated_at": payload["updated_at"],
    }


def _collection_run_payload(row: Any) -> dict[str, Any]:
    payload = dict(row)
    payload["diagnostic_snapshot"] = _read_json(payload.pop("diagnostic_snapshot_json"), {})
    return payload


def _notification_log_payload(row: Any) -> dict[str, Any]:
    payload = dict(row)
    payload["candidate_ids"] = _read_json(payload.pop("candidate_ids_json"), [])
    return payload


def _audit_log_payload(row: Any) -> dict[str, Any]:
    payload = dict(row)
    payload["before"] = _read_json(payload.pop("before_json"), None)
    payload["after"] = _read_json(payload.pop("after_json"), None)
    return payload


def _read_json(raw_value: str | None, default: Any) -> Any:
    if raw_value is None:
        return default
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return default


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)
