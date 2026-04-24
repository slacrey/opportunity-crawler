from __future__ import annotations

from pathlib import Path
from typing import Any
import sqlite3

from opportunity_crawler.shared.db.base import connect_sqlite


class ReviewService:
    REVIEW_STATUSES = {"pending", "accepted", "rejected"}
    FOLLOW_UP_STATUSES = {"none", "contacted", "visited", "quoted", "won", "lost"}

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def update_review_status(self, candidate_id: int, review_status: str) -> dict[str, Any]:
        if review_status not in self.REVIEW_STATUSES:
            raise ValueError("invalid_review_status")
        with connect_sqlite(self.database_path) as connection:
            cursor = connection.execute(
                """
                UPDATE opportunity_candidates
                SET review_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (review_status, candidate_id),
            )
            if cursor.rowcount == 0:
                raise KeyError("candidate_not_found")
            if review_status == "accepted":
                self._ensure_customer_for_candidate(connection, candidate_id)
            connection.commit()
            row = connection.execute("SELECT * FROM opportunity_candidates WHERE id = ?", (candidate_id,)).fetchone()
        return dict(row)

    def update_follow_up_status(
        self,
        candidate_id: int,
        *,
        follow_up_status: str,
        note: str | None,
        actor_id: int,
    ) -> dict[str, Any]:
        if follow_up_status not in self.FOLLOW_UP_STATUSES:
            raise ValueError("invalid_follow_up_status")
        with connect_sqlite(self.database_path) as connection:
            cursor = connection.execute(
                """
                UPDATE opportunity_candidates
                SET follow_up_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (follow_up_status, candidate_id),
            )
            if cursor.rowcount == 0:
                raise KeyError("candidate_not_found")
            customer_id = self._ensure_customer_for_candidate(connection, candidate_id)
            if customer_id is not None and follow_up_status != "none":
                connection.execute(
                    """
                    INSERT INTO customer_activities (
                        customer_id, candidate_id, activity_type, content, occurred_at, created_by
                    )
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                    """,
                    (customer_id, candidate_id, follow_up_status, note, actor_id),
                )
            connection.commit()
            row = connection.execute("SELECT * FROM opportunity_candidates WHERE id = ?", (candidate_id,)).fetchone()
        return dict(row)

    def _ensure_customer_for_candidate(self, connection: sqlite3.Connection, candidate_id: int) -> int | None:
        candidate = connection.execute(
            """
            SELECT organization_name, region, industry
            FROM opportunity_candidates
            WHERE id = ?
            """,
            (candidate_id,),
        ).fetchone()
        if candidate is None or not candidate["organization_name"]:
            return None
        connection.execute(
            """
            INSERT OR IGNORE INTO customers (name, region, industry, source)
            VALUES (?, ?, ?, 'opportunity')
            """,
            (candidate["organization_name"], candidate["region"], candidate["industry"]),
        )
        row = connection.execute(
            "SELECT id FROM customers WHERE name = ?",
            (candidate["organization_name"],),
        ).fetchone()
        return int(row["id"]) if row else None

