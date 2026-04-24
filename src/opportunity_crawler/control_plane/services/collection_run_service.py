from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import sqlite3
import uuid

from opportunity_crawler.collection.evidence import build_evidence_payload
from opportunity_crawler.shared.contracts.agent_protocol import (
    CollectionCommandMessage,
    CollectionEventKind,
    CollectionEventMessage,
    ControlPlaneCommandKind,
)
from opportunity_crawler.shared.db.base import connect_sqlite


class CollectionRunService:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def start_run(self, *, source_id: int, agent_id: str) -> dict[str, Any]:
        run_id = f"run-{uuid.uuid4()}"
        command_id = f"cmd-{uuid.uuid4()}"
        now = _utc_now()
        with connect_sqlite(self.database_path) as connection:
            source = connection.execute(
                """
                SELECT s.id, s.name, s.enabled, s.adapter_mode, s.login_mode,
                       arv.version AS rule_version
                FROM sources s
                LEFT JOIN source_advanced_rule_versions arv
                    ON arv.id = s.active_rule_version_id
                WHERE s.id = ?
                """,
                (source_id,),
            ).fetchone()
            if source is None:
                raise KeyError("source_not_found")
            if not bool(source["enabled"]):
                raise ValueError("source_disabled")
            if source["rule_version"] is None:
                raise ValueError("active_rule_missing")

            connection.execute(
                """
                INSERT INTO collection_runs (
                    run_id, source_id, agent_id, rule_version, status, scheduled_at
                )
                VALUES (?, ?, ?, ?, 'queued', ?)
                """,
                (run_id, source_id, agent_id, int(source["rule_version"]), now),
            )
            connection.commit()

            row = connection.execute(
                """
                SELECT cr.*, s.name AS source_name
                FROM collection_runs cr
                JOIN sources s ON s.id = cr.source_id
                WHERE cr.run_id = ?
                """,
                (run_id,),
            ).fetchone()

        command = CollectionCommandMessage(
            command=ControlPlaneCommandKind.START_COLLECTION_RUN,
            command_id=command_id,
            run_id=run_id,
            source_id=source_id,
            rule_version=int(source["rule_version"]),
            adapter_mode=str(source["adapter_mode"]),
            login_mode=str(source["login_mode"]),
        ).model_dump(mode="json")
        return {"run": collection_run_payload(row), "command": command}

    def record_event(self, *, agent_id: str | None, event: CollectionEventMessage) -> dict[str, Any]:
        if event.run_id is None:
            return {"run": None, "evidence_count": 0}

        now = _utc_now()
        diagnostic_snapshot = dict(event.diagnostic_snapshot)
        if event.detail:
            diagnostic_snapshot["detail"] = event.detail

        with connect_sqlite(self.database_path) as connection:
            run = connection.execute(
                "SELECT * FROM collection_runs WHERE run_id = ?",
                (event.run_id,),
            ).fetchone()
            if run is None:
                raise KeyError("collection_run_not_found")

            evidence_count = 0
            if event.rows and event.event_kind is not CollectionEventKind.TRIAL_RUN_COMPLETED:
                evidence_count = _persist_evidence_rows(connection, event)

            status = _status_for_event(event.event_kind, current_status=str(run["status"]))
            page_count = event.page_count if event.page_count else int(run["page_count"] or 0)
            item_count = event.item_count if event.item_count else max(int(run["item_count"] or 0), evidence_count)
            started_at = run["started_at"]
            finished_at = run["finished_at"]
            failure_kind = event.failure_kind if event.failure_kind is not None else run["failure_kind"]

            if event.event_kind is CollectionEventKind.RUN_STARTED and started_at is None:
                started_at = now
            if _is_terminal_event(event.event_kind):
                finished_at = now
                if started_at is None:
                    started_at = now

            connection.execute(
                """
                UPDATE collection_runs
                SET agent_id = COALESCE(?, agent_id),
                    status = ?,
                    started_at = ?,
                    finished_at = ?,
                    page_count = ?,
                    item_count = ?,
                    failure_kind = ?,
                    diagnostic_snapshot_json = ?
                WHERE run_id = ?
                """,
                (
                    agent_id,
                    status,
                    started_at,
                    finished_at,
                    page_count,
                    item_count,
                    failure_kind,
                    _json(diagnostic_snapshot),
                    event.run_id,
                ),
            )
            _update_source_health(connection, event, now)
            connection.commit()

            updated = connection.execute(
                """
                SELECT cr.*, s.name AS source_name
                FROM collection_runs cr
                JOIN sources s ON s.id = cr.source_id
                WHERE cr.run_id = ?
                """,
                (event.run_id,),
            ).fetchone()

        return {"run": collection_run_payload(updated), "evidence_count": evidence_count}


def collection_run_payload(row: Any) -> dict[str, Any]:
    payload = dict(row)
    payload["diagnostic_snapshot"] = _read_json(payload.pop("diagnostic_snapshot_json"), {})
    return payload


def _persist_evidence_rows(connection: sqlite3.Connection, event: CollectionEventMessage) -> int:
    written = 0
    for row in event.rows:
        evidence = build_evidence_payload(row)
        raw_text = _optional_str(evidence.get("raw_text") or evidence.get("body") or evidence.get("text"))
        source_item_key = _optional_str(evidence.get("source_item_key"))
        content_fingerprint = _optional_str(evidence.get("content_fingerprint"))
        if not content_fingerprint:
            content_fingerprint = hashlib.sha256((raw_text or "").encode("utf-8")).hexdigest()
        title = _required_title(evidence)
        attachments_json = _json(_attachments(evidence))
        existing = None
        if source_item_key:
            existing = connection.execute(
                """
                SELECT id
                FROM raw_evidence_items
                WHERE source_id = ? AND source_item_key = ?
                """,
                (event.source_id, source_item_key),
            ).fetchone()

        values = (
            event.run_id,
            event.source_id,
            source_item_key,
            _optional_str(evidence.get("url")),
            title,
            _optional_str(evidence.get("published_at")),
            raw_text,
            _optional_str(evidence.get("raw_html_path")),
            attachments_json,
            content_fingerprint,
        )
        if existing is None:
            connection.execute(
                """
                INSERT INTO raw_evidence_items (
                    run_id, source_id, source_item_key, url, title, published_at,
                    raw_text, raw_html_path, attachments_json, content_fingerprint
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
        else:
            connection.execute(
                """
                UPDATE raw_evidence_items
                SET run_id = ?,
                    source_id = ?,
                    source_item_key = ?,
                    url = ?,
                    title = ?,
                    published_at = ?,
                    raw_text = ?,
                    raw_html_path = ?,
                    attachments_json = ?,
                    content_fingerprint = ?
                WHERE id = ?
                """,
                (*values, existing["id"]),
            )
        written += 1
    return written


def _update_source_health(connection: sqlite3.Connection, event: CollectionEventMessage, now: str) -> None:
    if event.event_kind is CollectionEventKind.RUN_SUCCEEDED:
        connection.execute(
            """
            UPDATE sources
            SET health_status = 'healthy',
                last_success_at = ?,
                last_failure_at = NULL,
                last_failure_reason = NULL
            WHERE id = ?
            """,
            (now, event.source_id),
        )
    elif event.event_kind in {
        CollectionEventKind.RUN_FAILED,
        CollectionEventKind.LOGIN_REQUIRED,
        CollectionEventKind.OPERATOR_INTERVENTION_REQUIRED,
    }:
        failure_reason = event.failure_kind or event.detail or event.event_kind.value
        connection.execute(
            """
            UPDATE sources
            SET health_status = 'failed',
                last_failure_at = ?,
                last_failure_reason = ?
            WHERE id = ?
            """,
            (now, failure_reason, event.source_id),
        )
        if event.event_kind is CollectionEventKind.LOGIN_REQUIRED:
            connection.execute(
                "UPDATE sources SET login_status = 'pending_login' WHERE id = ?",
                (event.source_id,),
            )


def _status_for_event(event_kind: CollectionEventKind, *, current_status: str) -> str:
    statuses = {
        CollectionEventKind.RUN_STARTED: "running",
        CollectionEventKind.RUN_SUCCEEDED: "succeeded",
        CollectionEventKind.RUN_FAILED: "failed",
        CollectionEventKind.LOGIN_REQUIRED: "login_required",
        CollectionEventKind.OPERATOR_INTERVENTION_REQUIRED: "operator_intervention_required",
        CollectionEventKind.RUN_STOPPED: "stopped",
    }
    return statuses.get(event_kind, current_status)


def _is_terminal_event(event_kind: CollectionEventKind) -> bool:
    return event_kind in {
        CollectionEventKind.RUN_SUCCEEDED,
        CollectionEventKind.RUN_FAILED,
        CollectionEventKind.LOGIN_REQUIRED,
        CollectionEventKind.OPERATOR_INTERVENTION_REQUIRED,
        CollectionEventKind.RUN_STOPPED,
    }


def _required_title(evidence: dict[str, Any]) -> str:
    title = _optional_str(evidence.get("title"))
    if title:
        return title
    fallback = _optional_str(evidence.get("url") or evidence.get("source_item_key"))
    return fallback or "Untitled evidence"


def _attachments(evidence: dict[str, Any]) -> Any:
    attachments = evidence.get("attachments")
    if attachments is not None:
        return attachments
    attachments_json = evidence.get("attachments_json")
    if isinstance(attachments_json, str):
        return _read_json(attachments_json, [])
    return attachments_json or []


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _read_json(raw_value: str | None, default: Any) -> Any:
    if raw_value is None:
        return default
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return default


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
