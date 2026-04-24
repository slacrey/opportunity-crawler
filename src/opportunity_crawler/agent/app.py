from __future__ import annotations

from typing import Any

from opportunity_crawler.agent.runtime.collection_runner import CollectionRunner
from opportunity_crawler.agent.runtime.command_handlers import CommandHandlers
from opportunity_crawler.shared.contracts.agent_protocol import CollectionCommandMessage, parse_control_plane_message


class CollectionAgentApp:
    def __init__(self, *, runner: Any | None = None, client: Any | None = None) -> None:
        self.runner = runner or CollectionRunner()
        self.client = client
        self.handlers = CommandHandlers(self.runner)

    async def handle_command(self, payload: dict[str, Any] | CollectionCommandMessage) -> dict[str, Any]:
        command = payload if isinstance(payload, CollectionCommandMessage) else parse_control_plane_message(payload)
        if not isinstance(command, CollectionCommandMessage):
            raise TypeError(f"expected collection command, got {command.message_type}")
        result = await self.handlers.handle(command)
        if self.client is not None:
            await self.client.send_collection_event(**result)
        return result

