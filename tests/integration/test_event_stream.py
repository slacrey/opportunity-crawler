from __future__ import annotations

import json
from pathlib import Path

from tests.integration.api_helpers import auth_headers, build_client

from opportunity_crawler.shared.db.base import connect_sqlite


def test_event_stream_returns_initial_runtime_snapshot(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    headers = auth_headers(client)
    _seed_collection_runs(client.app.state.database_path)

    response = client.get("/api/events", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: snapshot" in response.text
    assert _snapshot_payload(response.text) == {
        "type": "snapshot",
        "agents_online": 0,
        "runs": {"queued": 1, "running": 1, "succeeded": 1, "failed": 1},
    }


def _seed_collection_runs(database_path: Path) -> None:
    with connect_sqlite(database_path) as connection:
        source_id = connection.execute("SELECT id FROM sources ORDER BY id LIMIT 1").fetchone()["id"]
        for status in ("queued", "running", "succeeded", "failed"):
            connection.execute(
                """
                INSERT INTO collection_runs (run_id, source_id, rule_version, status)
                VALUES (?, ?, 1, ?)
                """,
                (f"run-{status}", source_id, status),
            )
        connection.commit()


def _snapshot_payload(body: str) -> dict[str, object]:
    data_line = next(line for line in body.splitlines() if line.startswith("data: "))
    return json.loads(data_line.removeprefix("data: "))
