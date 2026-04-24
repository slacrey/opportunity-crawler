from __future__ import annotations

from pathlib import Path

from tests.integration.api_helpers import build_client


def test_health_endpoint_reports_database_and_runtime_readiness(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["database"]["ok"] is True
    assert payload["migrations"]["ok"] is True
    assert "secrets" not in payload
