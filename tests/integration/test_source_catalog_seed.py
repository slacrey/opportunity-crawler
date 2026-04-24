from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.shared.db.base import apply_migrations, connect_sqlite


def migrated_connection(tmp_path: Path) -> sqlite3.Connection:
    connection = connect_sqlite(tmp_path / "opportunity.db")
    apply_migrations(connection)
    return connection


def test_seeded_sources_include_public_login_and_manual_modes(tmp_path: Path) -> None:
    connection = migrated_connection(tmp_path)

    try:
        sources = {
            row["name"]: row
            for row in connection.execute(
                """
                SELECT name, priority, adapter_mode, login_mode, health_status, active_rule_version_id
                FROM sources
                """,
            ).fetchall()
        }

        assert sources["中国政府采购网"]["priority"] == "P0"
        assert sources["中国政府采购网"]["adapter_mode"] == "public_search_list_detail"
        assert sources["中国政府采购网"]["login_mode"] == "not_required"
        assert sources["中国政府采购网"]["active_rule_version_id"] is not None

        assert sources["建设网"]["adapter_mode"] == "login_search_list_detail"
        assert sources["建设网"]["login_mode"] == "login_required"

        assert sources["微信公众号手动导入"]["adapter_mode"] == "manual_import"
        assert sources["微信公众号手动导入"]["login_mode"] == "not_required"
    finally:
        connection.close()


def test_seeded_sources_have_basic_rules(tmp_path: Path) -> None:
    connection = migrated_connection(tmp_path)

    try:
        row = connection.execute(
            """
            SELECT br.frequency, br.digest_enabled, br.digest_score_threshold
            FROM source_basic_rules br
            JOIN sources s ON s.id = br.source_id
            WHERE s.name = '中国政府采购网'
            """,
        ).fetchone()

        assert row["frequency"] == "daily"
        assert row["digest_enabled"] == 1
        assert row["digest_score_threshold"] == 70
    finally:
        connection.close()
