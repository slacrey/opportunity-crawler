from __future__ import annotations

import json
from typing import Any, Callable

from opportunity_crawler.shared.contracts.agent_protocol import (
    CollectionEventKind,
    CollectionEventMessage,
    HeartbeatMessage,
    RegisterMessage,
    parse_control_plane_message,
)


class AgentWebSocketClient:
    def __init__(
        self,
        *,
        control_plane_ws_url: str,
        agent_id: str,
        host_id: str,
        capacity: int,
        heartbeat_interval_seconds: float = 20.0,
        connect_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.control_plane_ws_url = control_plane_ws_url
        self.agent_id = agent_id
        self.host_id = host_id
        self.capacity = capacity
        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        self.connect_factory = connect_factory or _default_connect
        self._connection: Any | None = None

    async def connect_once(self) -> dict[str, Any]:
        self._connection = await self.connect_factory(
            self.control_plane_ws_url,
            ping_interval=None,
            proxy=None,
        )
        register = RegisterMessage(
            message_type="register",
            agent_id=self.agent_id,
            host_id=self.host_id,
            capacity=self.capacity,
        )
        await self._connection.send(json.dumps(register.model_dump(mode="json")))
        payload = json.loads(await self._connection.recv())
        return parse_control_plane_message(payload).model_dump(mode="json")

    async def send_heartbeat(self) -> None:
        if self._connection is None:
            raise RuntimeError("websocket connection is not established")
        heartbeat = HeartbeatMessage(agent_id=self.agent_id)
        await self._connection.send(json.dumps(heartbeat.model_dump(mode="json")))

    async def send_collection_event(self, **payload: Any) -> None:
        if self._connection is None:
            raise RuntimeError("websocket connection is not established")
        if "event_kind" in payload:
            payload["event_kind"] = CollectionEventKind(payload["event_kind"])
        event = CollectionEventMessage(message_type="collection_event", **payload)
        await self._connection.send(json.dumps(event.model_dump(mode="json")))

    async def close(self) -> None:
        if self._connection is None:
            return
        connection = self._connection
        self._connection = None
        await connection.close()


async def _default_connect(*args: Any, **kwargs: Any) -> Any:
    try:
        from websockets.asyncio.client import connect
    except ModuleNotFoundError as exc:
        raise RuntimeError("websockets package is required for real Agent connections") from exc
    return await connect(*args, **kwargs)
