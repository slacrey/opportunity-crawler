from __future__ import annotations

import sqlite3
from typing import Any


class SchedulerService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def due_sources(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT s.id, s.name, s.adapter_mode, s.login_mode, s.login_status, s.health_status
            FROM sources s
            JOIN source_advanced_rule_versions ar ON ar.id = s.active_rule_version_id
            WHERE s.enabled = 1
              AND ar.status = 'active'
              AND (
                s.login_mode = 'not_required'
                OR (s.login_mode = 'login_required' AND s.login_status = 'logged_in')
              )
              AND s.health_status != 'failed_guarded'
            ORDER BY s.priority, s.id
            """,
        ).fetchall()
        return [dict(row) for row in rows]

    def record_run_result(
        self,
        *,
        source_id: int,
        status: str,
        item_count: int,
        failure_kind: str | None,
    ) -> None:
        if status == "succeeded":
            self.connection.execute(
                """
                UPDATE sources
                SET health_status = 'healthy',
                    last_success_at = CURRENT_TIMESTAMP,
                    last_failure_reason = NULL
                WHERE id = ?
                """,
                (source_id,),
            )
        else:
            self.connection.execute(
                """
                UPDATE sources
                SET health_status = 'failed',
                    last_failure_at = CURRENT_TIMESTAMP,
                    last_failure_reason = ?
                WHERE id = ?
                """,
                (failure_kind or "unknown", source_id),
            )
        _ = item_count
        self.connection.commit()

