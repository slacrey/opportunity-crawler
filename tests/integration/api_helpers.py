from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.control_plane.app import create_app
from opportunity_crawler.control_plane.services.auth_service import AuthService
from opportunity_crawler.shared.db.base import apply_migrations, connect_sqlite


def build_client(tmp_path: Path) -> TestClient:
    database_path = tmp_path / "opportunity.db"
    connection = connect_sqlite(database_path)
    apply_migrations(connection)
    _seed_user(connection, "admin", "admin-pass", "administrator")
    _seed_user(connection, "biz", "biz-pass", "business_manager")
    connection.close()
    return TestClient(create_app(database_path=database_path))


def auth_headers(client: TestClient, username: str = "admin", password: str = "admin-pass") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def first_source_id(client: TestClient, headers: dict[str, str], name: str = "中国政府采购网") -> int:
    response = client.get("/api/sources", headers=headers)
    assert response.status_code == 200, response.text
    for source in response.json()["items"]:
        if source["name"] == name:
            return int(source["id"])
    raise AssertionError(f"source not found: {name}")


def _seed_user(connection: sqlite3.Connection, username: str, password: str, role_name: str) -> None:
    password_hash = AuthService.hash_password(password)
    connection.execute(
        """
        INSERT INTO users (username, password_hash, display_name)
        VALUES (?, ?, ?)
        """,
        (username, password_hash, username),
    )
    user_id = connection.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()[0]
    role_id = connection.execute("SELECT id FROM roles WHERE name = ?", (role_name,)).fetchone()[0]
    connection.execute(
        "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
        (user_id, role_id),
    )
    connection.commit()

