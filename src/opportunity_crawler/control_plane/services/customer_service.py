from __future__ import annotations

from pathlib import Path
from typing import Any

from opportunity_crawler.shared.db.base import connect_sqlite


class CustomerService:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def history_for_customer(self, name: str) -> dict[str, Any]:
        with connect_sqlite(self.database_path) as connection:
            customer = connection.execute("SELECT * FROM customers WHERE name = ?", (name,)).fetchone()
            if customer is None:
                customer_payload = {"name": name, "region": None, "industry": None}
                customer_id = None
            else:
                customer_payload = dict(customer)
                customer_id = int(customer["id"])
            opportunities = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT id, title, score, priority_label, review_status, follow_up_status, created_at
                    FROM opportunity_candidates
                    WHERE organization_name = ?
                    ORDER BY created_at DESC, id DESC
                    """,
                    (name,),
                ).fetchall()
            ]
            activities = []
            if customer_id is not None:
                activities = [
                    dict(row)
                    for row in connection.execute(
                        """
                        SELECT id, candidate_id, activity_type, content, occurred_at, created_by
                        FROM customer_activities
                        WHERE customer_id = ?
                        ORDER BY occurred_at DESC, id DESC
                        """,
                        (customer_id,),
                    ).fetchall()
                ]
        return {
            "customer": customer_payload,
            "opportunity_count": len(opportunities),
            "opportunities": opportunities,
            "activities": activities,
        }

