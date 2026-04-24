from __future__ import annotations

from pathlib import Path

from tests.integration.api_helpers import build_client


def test_agent_websocket_registers_and_heartbeats(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    with client.websocket_connect("/api/agents/ws") as websocket:
        websocket.send_json(
            {
                "type": "register",
                "agent_id": "agent-local",
                "host_id": "host-local",
                "hostname": "localhost",
                "platform": "darwin",
                "app_version": "0.1.0",
                "capacity": 2,
            }
        )
        assert websocket.receive_json()["type"] == "registered"

        websocket.send_json({"type": "heartbeat", "agent_id": "agent-local"})
        heartbeat = websocket.receive_json()
        assert heartbeat["type"] == "heartbeat_ack"
        assert heartbeat["agent_id"] == "agent-local"

