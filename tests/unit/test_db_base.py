from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.shared.db.base import apply_migrations, connect_sqlite


def test_connect_sqlite_creates_parent_and_enables_required_pragmas(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "opportunity.db"

    connection = connect_sqlite(database_path)

    try:
        assert database_path.exists()
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    finally:
        connection.close()


def test_apply_migrations_creates_schema_table_for_empty_migration_directory(tmp_path: Path) -> None:
    connection = sqlite3.connect(tmp_path / "opportunity.db")
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    try:
        apply_migrations(connection, migrations_path=migrations_dir)

        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'",
        ).fetchone()
        assert row == ("schema_migrations",)
        assert connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 0
    finally:
        connection.close()


def test_apply_migrations_applies_each_new_migration_once(tmp_path: Path) -> None:
    connection = sqlite3.connect(tmp_path / "opportunity.db")
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    migration_path = migrations_dir / "20260424_001_create_example.py"
    migration_path.write_text(
        '''
MIGRATION_ID = "20260424_001"


def upgrade(connection):
    connection.execute("CREATE TABLE example_items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
'''.strip(),
        encoding="utf-8",
    )

    try:
        apply_migrations(connection, migrations_path=migrations_dir)
        apply_migrations(connection, migrations_path=migrations_dir)

        assert connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 1
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'example_items'",
        ).fetchone()
        assert row == ("example_items",)
    finally:
        connection.close()
