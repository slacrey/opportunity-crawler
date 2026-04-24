from __future__ import annotations

from pathlib import Path

from tests.integration.api_helpers import auth_headers, build_client


def test_event_stream_returns_initial_runtime_snapshot(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    headers = auth_headers(client)

    response = client.get("/api/events", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: snapshot" in response.text

