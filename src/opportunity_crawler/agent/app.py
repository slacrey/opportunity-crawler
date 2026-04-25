from __future__ import annotations

import logging
from typing import Any

from opportunity_crawler.agent.runtime.collection_runner import CollectionRunner
from opportunity_crawler.agent.runtime.command_handlers import CommandHandlers
from opportunity_crawler.shared.contracts.agent_protocol import (
    CollectionCommandMessage,
    CollectionEventKind,
    ControlPlaneCommandKind,
    parse_control_plane_message,
)


logger = logging.getLogger(__name__)


class CollectionAgentApp:
    def __init__(self, *, runner: Any | None = None, client: Any | None = None) -> None:
        self.runner = runner or CollectionRunner()
        self.client = client
        self.handlers = CommandHandlers(self.runner)

    async def handle_command(self, payload: dict[str, Any] | CollectionCommandMessage) -> dict[str, Any]:
        command = payload if isinstance(payload, CollectionCommandMessage) else parse_control_plane_message(payload)
        if not isinstance(command, CollectionCommandMessage):
            raise TypeError(f"expected collection command, got {command.message_type}")
        logger.info(
            "agent.command.received command=%s command_id=%s run_id=%s source_id=%s adapter_mode=%s",
            _value(command.command),
            command.command_id,
            command.run_id,
            command.source_id,
            command.adapter_mode,
        )
        if self.client is not None and command.command is ControlPlaneCommandKind.START_COLLECTION_RUN:
            logger.info(
                "agent.event.sending event_kind=%s command_id=%s run_id=%s source_id=%s adapter_mode=%s",
                CollectionEventKind.RUN_STARTED.value,
                command.command_id,
                command.run_id,
                command.source_id,
                command.adapter_mode,
            )
            await self.client.send_collection_event(
                event_kind=CollectionEventKind.RUN_STARTED,
                command_id=command.command_id,
                run_id=command.run_id,
                source_id=command.source_id,
                adapter_mode=command.adapter_mode,
            )
        result = await self.handlers.handle(command)
        logger.info(
            "agent.command.handled command=%s command_id=%s run_id=%s source_id=%s event_kind=%s item_count=%s",
            _value(command.command),
            command.command_id,
            command.run_id,
            command.source_id,
            _value(result.get("event_kind")),
            result.get("item_count"),
        )
        if self.client is not None:
            logger.info(
                "agent.event.sending event_kind=%s command_id=%s run_id=%s source_id=%s item_count=%s",
                _value(result.get("event_kind")),
                result.get("command_id"),
                result.get("run_id"),
                result.get("source_id"),
                result.get("item_count"),
            )
            await self.client.send_collection_event(**result)
        return result


def _value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value
