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


def test_initial_migration_creates_core_domain_tables(tmp_path: Path) -> None:
    connection = migrated_connection(tmp_path)

    try:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'",
            ).fetchall()
        }

        assert {
            "users",
            "roles",
            "user_roles",
            "sources",
            "source_basic_rules",
            "source_advanced_rule_versions",
            "source_accounts",
            "agent_hosts",
            "agent_instances",
            "collection_runs",
            "raw_evidence_items",
            "opportunity_candidates",
            "candidate_analysis",
            "customers",
            "customer_activities",
            "weekly_goals",
            "notification_logs",
            "audit_logs",
        }.issubset(table_names)
    finally:
        connection.close()


def test_source_name_and_url_are_unique(tmp_path: Path) -> None:
    connection = migrated_connection(tmp_path)

    try:
        connection.execute(
            """
            INSERT INTO sources (name, category, home_url, priority, adapter_mode, login_mode)
            VALUES ('测试来源', 'test', 'https://example.test', 'P0', 'manual_import', 'not_required')
            """,
        )

        try:
            connection.execute(
                """
                INSERT INTO sources (name, category, home_url, priority, adapter_mode, login_mode)
                VALUES ('测试来源', 'test', 'https://example.test', 'P0', 'manual_import', 'not_required')
                """,
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("expected duplicate source to fail")
    finally:
        connection.close()


def test_only_one_active_advanced_rule_version_per_source(tmp_path: Path) -> None:
    connection = migrated_connection(tmp_path)

    try:
        source_id = connection.execute(
            "SELECT id FROM sources WHERE name = '中国政府采购网'",
        ).fetchone()[0]
        active_count = connection.execute(
            """
            SELECT COUNT(*) FROM source_advanced_rule_versions
            WHERE source_id = ? AND status = 'active'
            """,
            (source_id,),
        ).fetchone()[0]
        assert active_count == 1

        try:
            connection.execute(
                """
                INSERT INTO source_advanced_rule_versions (
                    source_id, version, status, adapter_mode, entry_url, login_mode,
                    selectors_json, pagination_policy_json, normalization_mapping_json,
                    risk_patterns_json, rate_limit_policy_json, created_by
                )
                VALUES (?, 99, 'active', 'public_search_list_detail', 'https://example.test',
                        'not_required', '{}', '{}', '{}', '{}', '{}', 'test')
                """,
                (source_id,),
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("expected second active rule version to fail")
    finally:
        connection.close()
