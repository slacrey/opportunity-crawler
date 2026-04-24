from __future__ import annotations

import json
import sys
from pathlib import Path
import asyncio

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.agent.channel.websocket_client import AgentWebSocketClient


class FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []
        self.received: list[str] = [
            json.dumps({"message_type": "registered", "agent_id": "agent-1", "host_id": "host-1"})
        ]

    async def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))

    async def recv(self) -> str:
        return self.received.pop(0)

    async def close(self) -> None:
        return None


def test_websocket_client_registers_and_sends_heartbeat() -> None:
    asyncio.run(_assert_websocket_client_registers_and_sends_heartbeat())


async def _assert_websocket_client_registers_and_sends_heartbeat() -> None:
    socket = FakeWebSocket()

    async def connect_factory(*args: object, **kwargs: object) -> FakeWebSocket:
        return socket

    client = AgentWebSocketClient(
        control_plane_ws_url="ws://127.0.0.1:8000/api/agents/ws",
        agent_id="agent-1",
        host_id="host-1",
        capacity=2,
        connect_factory=connect_factory,
    )

    registered = await client.connect_once()
    await client.send_heartbeat()

    assert registered["message_type"] == "registered"
    assert socket.sent[0]["message_type"] == "register"
    assert socket.sent[1]["message_type"] == "heartbeat"
