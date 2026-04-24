from __future__ import annotations

from pathlib import Path

from tests.integration.api_helpers import build_client


def test_local_login_returns_token_and_roles(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["user"]["username"] == "admin"
    assert "administrator" in payload["user"]["roles"]


def test_invalid_login_returns_structured_error(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"

