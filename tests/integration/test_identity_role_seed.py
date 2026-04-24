from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.shared.db.base import apply_migrations, connect_sqlite


def test_identity_roles_are_seeded_without_plaintext_credentials(tmp_path: Path) -> None:
    connection = connect_sqlite(tmp_path / "opportunity.db")
    apply_migrations(connection)

    try:
        role_names = {row[0] for row in connection.execute("SELECT name FROM roles").fetchall()}
        assert {"operator", "business_manager", "manager", "administrator"}.issubset(role_names)

        users = connection.execute("SELECT username, password_hash FROM users").fetchall()
        for username, password_hash in users:
            assert password_hash != "password"
            assert username not in password_hash
    finally:
        connection.close()
