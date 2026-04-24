from __future__ import annotations

from pathlib import Path
from typing import Any

from opportunity_crawler.shared.db.base import connect_sqlite


class GoalService:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def weekly_progress(self, *, week_start: str) -> dict[str, Any]:
        with connect_sqlite(self.database_path) as connection:
            accepted = int(
                connection.execute(
                    "SELECT COUNT(*) FROM opportunity_candidates WHERE review_status = 'accepted'",
                ).fetchone()[0]
            )
            visits = int(
                connection.execute(
                    "SELECT COUNT(*) FROM customer_activities WHERE activity_type = 'visited'",
                ).fetchone()[0]
            )
            quotes = int(
                connection.execute(
                    "SELECT COUNT(*) FROM customer_activities WHERE activity_type = 'quoted'",
                ).fetchone()[0]
            )
        return {
            "week_start": week_start,
            "accepted_opportunities": accepted,
            "visits": visits,
            "quotes": quotes,
        }

