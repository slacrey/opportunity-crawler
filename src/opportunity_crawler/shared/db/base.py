from __future__ import annotations

from importlib import util
from pathlib import Path
import sqlite3
import sys


def project_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root is not None:
        return Path(frozen_root)
    return Path(__file__).resolve().parents[4]


def migrations_dir() -> Path:
    return project_root() / "migrations" / "versions"


def connect_sqlite(database_path: str | Path) -> sqlite3.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def apply_migrations(connection: sqlite3.Connection, migrations_path: str | Path | None = None) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )
    for migration in _load_migrations(Path(migrations_path) if migrations_path else migrations_dir()):
        already_applied = connection.execute(
            "SELECT 1 FROM schema_migrations WHERE version = ?",
            (migration.MIGRATION_ID,),
        ).fetchone()
        if already_applied:
            continue

        migration.upgrade(connection)
        connection.execute(
            "INSERT INTO schema_migrations (version) VALUES (?)",
            (migration.MIGRATION_ID,),
        )
        connection.commit()


def _load_migrations(path: Path) -> list[object]:
    migrations: list[object] = []
    if not path.exists():
        return migrations

    for migration_path in sorted(path.glob("*.py")):
        spec = util.spec_from_file_location(
            f"opportunity_crawler_migration_{migration_path.stem}",
            migration_path,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"unable to load migration from {migration_path}")
        module = util.module_from_spec(spec)
        spec.loader.exec_module(module)
        migrations.append(module)
    return migrations
