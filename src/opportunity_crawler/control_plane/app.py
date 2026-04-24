from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel

from opportunity_crawler.control_plane.routes.api.errors import ApiError, api_error
from opportunity_crawler.control_plane.services.auth_service import AuthService, AuthenticatedUser
from opportunity_crawler.control_plane.services.customer_service import CustomerService
from opportunity_crawler.control_plane.services.goal_service import GoalService
from opportunity_crawler.control_plane.services.normalization_service import CandidateCreationService, ManualCandidateInput
from opportunity_crawler.control_plane.services.permission_service import PermissionService
from opportunity_crawler.control_plane.services.review_service import ReviewService
from opportunity_crawler.control_plane.services.runtime_registry import RuntimeRegistry
from opportunity_crawler.control_plane.workers.notification_worker import NotificationWorker
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
            _require_rule_version(connection, source_id, version)
        return {
            "source_id": source_id,
            "version": version,
            "max_items": payload.max_items,
            "preview_rows": [],
            "diagnostic_snapshot": {"trial_run": True},
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

    @app.get("/api/goals/weekly-progress")
    async def weekly_progress(week_start: str, request: Request) -> dict[str, Any]:
        _require_permission(request, "goals:read")
        return GoalService(app.state.database_path).weekly_progress(week_start=week_start)

    @app.post("/api/notifications/dingtalk/digest")
    async def send_dingtalk_digest(payload: DigestRequest, request: Request) -> dict[str, Any]:
        _require_permission(request, "notifications:read")
        return NotificationWorker(app.state.database_path).send_daily_digest(simulate_failure=payload.simulate_failure)

    @app.websocket("/api/agents/ws")
    async def agent_websocket(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                message = await websocket.receive_json()
                if message.get("type") == "register":
                    presence = app.state.runtime_registry.register(message)
                    await websocket.send_json({"type": "registered", "agent_id": presence["agent_id"]})
                elif message.get("type") == "heartbeat":
                    presence = app.state.runtime_registry.heartbeat(str(message["agent_id"]))
                    await websocket.send_json({"type": "heartbeat_ack", "agent_id": presence["agent_id"]})
                else:
                    await websocket.send_json({"type": "error", "code": "unsupported_message"})
        except WebSocketDisconnect:
            return

    @app.get("/api/events")
    async def events(request: Request) -> Response:
        _require_user(request)
        body = "event: snapshot\ndata: {\"status\":\"ok\"}\n\n"
        return Response(content=body, media_type="text/event-stream")

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        with connect_sqlite(app.state.database_path) as connection:
            migration_count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
        return {
            "database": {"ok": True},
            "migrations": {"ok": migration_count > 0},
            "agents": {"online": app.state.runtime_registry.online_count()},
            "browser": {"ok": None, "detail": "not checked in API process"},
        }

    return app


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


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)
