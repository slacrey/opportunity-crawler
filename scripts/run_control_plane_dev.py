from __future__ import annotations

import argparse
import os
from pathlib import Path
import sqlite3
import sys
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DEFAULT_CONFIG = ROOT / "packaging" / "defaults" / "control_plane.toml"
DEFAULT_DEV_USERS = (
    ("admin", "admin-pass", "administrator"),
    ("biz", "biz-pass", "business_manager"),
)

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.bootstrap.control_plane import build_runtime
from opportunity_crawler.control_plane.app import create_app
from opportunity_crawler.control_plane.services.auth_service import AuthService
from opportunity_crawler.shared.db.base import apply_migrations, connect_sqlite


def prepare_database(
    database_path: str | Path,
    *,
    dev_users: Sequence[tuple[str, str, str]] = DEFAULT_DEV_USERS,
) -> None:
    connection = connect_sqlite(database_path)
    try:
        apply_migrations(connection)
        for username, password, role_name in dev_users:
            _seed_dev_user(connection, username, password, role_name)
        connection.commit()
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Opportunity Crawler control plane for local development.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--no-seed-users", action="store_true")
    parser.add_argument("--log-level", default=os.environ.get("UVICORN_LOG_LEVEL", "info"))
    args = parser.parse_args(argv)

    runtime = build_runtime(config_path=args.config)
    settings = runtime.settings
    database_path = _resolve_root_relative(settings.shared.database_path)
    dev_users = () if args.no_seed_users else DEFAULT_DEV_USERS
    prepare_database(database_path, dev_users=dev_users)

    import uvicorn

    uvicorn.run(
        create_app(database_path),
        host=settings.control_plane.host,
        port=settings.control_plane.port,
        log_level=args.log_level,
    )


def _resolve_root_relative(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _seed_dev_user(connection: sqlite3.Connection, username: str, password: str, role_name: str) -> None:
    role = connection.execute("SELECT id FROM roles WHERE name = ?", (role_name,)).fetchone()
    if role is None:
        raise RuntimeError(f"development role does not exist: {role_name}")

    password_hash = AuthService.hash_password(password)
    user = connection.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if user is None:
        connection.execute(
            """
            INSERT INTO users (username, password_hash, display_name, status)
            VALUES (?, ?, ?, 'active')
            """,
            (username, password_hash, username),
        )
        user_id = int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])
    else:
        user_id = int(user["id"])
        connection.execute(
            """
            UPDATE users
            SET password_hash = ?, status = 'active'
            WHERE id = ?
            """,
            (password_hash, user_id),
        )

    connection.execute(
        "INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)",
        (user_id, int(role["id"])),
    )


if __name__ == "__main__":
    main()
