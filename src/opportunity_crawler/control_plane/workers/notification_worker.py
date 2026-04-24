from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from opportunity_crawler.integrations.dingtalk import DingTalkClient, DingTalkDigestBuilder, DingTalkTransportError
from opportunity_crawler.shared.db.base import connect_sqlite


class NotificationWorker:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.builder = DingTalkDigestBuilder()

    def send_daily_digest(self, *, simulate_failure: bool = False) -> dict[str, Any]:
        with connect_sqlite(self.database_path) as connection:
            candidates = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT id, title, organization_name, score, priority_label
                    FROM opportunity_candidates
                    WHERE review_status = 'accepted' AND score >= 70
                    ORDER BY score DESC, id DESC
                    """,
                ).fetchall()
            ]
            message = self.builder.build_daily_digest(candidates)
            status = "sent"
            failure_reason = None
            try:
                client = DingTalkClient(
                    transport=(
                        lambda _: (_ for _ in ()).throw(DingTalkTransportError("simulated transport failure"))
                    )
                    if simulate_failure
                    else None
                )
                client.send_message(message)
            except DingTalkTransportError as exc:
                status = "failed"
                failure_reason = str(exc)
            candidate_ids = [candidate["id"] for candidate in candidates]
            connection.execute(
                """
                INSERT INTO notification_logs (
                    channel, template, candidate_ids_json, status, sent_at, failure_reason
                )
                VALUES ('dingtalk', 'daily_digest', ?, ?, CASE WHEN ? = 'sent' THEN CURRENT_TIMESTAMP ELSE NULL END, ?)
                """,
                (_json(candidate_ids), status, status, failure_reason),
            )
            log_id = int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])
            connection.commit()
        return {
            "id": log_id,
            "status": status,
            "failure_reason": failure_reason,
            "candidate_count": len(candidates),
            "message": message,
        }


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)
