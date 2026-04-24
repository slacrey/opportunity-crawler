from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.control_plane.services.scheduler_service import SchedulerService
from opportunity_crawler.shared.db.base import apply_migrations, connect_sqlite


def test_scheduler_returns_due_public_sources_and_skips_pending_login_sources(tmp_path: Path) -> None:
    connection = connect_sqlite(tmp_path / "opportunity.db")
    apply_migrations(connection)

    try:
        due_sources = SchedulerService(connection).due_sources()
        names = {source["name"] for source in due_sources}

        assert "中国政府采购网" in names
        assert "建设网" not in names
    finally:
        connection.close()


def test_scheduler_treats_empty_result_success_as_not_failed(tmp_path: Path) -> None:
    connection = connect_sqlite(tmp_path / "opportunity.db")
    apply_migrations(connection)

    try:
        source_id = connection.execute(
            "SELECT id FROM sources WHERE name = '中国政府采购网'",
        ).fetchone()[0]
        SchedulerService(connection).record_run_result(
            source_id=source_id,
            status="succeeded",
            item_count=0,
            failure_kind=None,
        )
        row = connection.execute(
            "SELECT health_status, last_failure_reason FROM sources WHERE id = ?",
            (source_id,),
        ).fetchone()

        assert row["health_status"] == "healthy"
        assert row["last_failure_reason"] is None
    finally:
        connection.close()

