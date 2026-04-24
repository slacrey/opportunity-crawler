from __future__ import annotations

from typing import Any

from opportunity_crawler.agent.runtime.collection_runner import CollectionRunner
from opportunity_crawler.shared.contracts.agent_protocol import CollectionCommandMessage, ControlPlaneCommandKind


class CommandHandlers:
    def __init__(self, runner: CollectionRunner) -> None:
        self.runner = runner

    async def handle(self, command: CollectionCommandMessage) -> dict[str, Any]:
        if command.command is ControlPlaneCommandKind.START_COLLECTION_RUN:
            return await self.runner.start_collection_run(command)
        if command.command is ControlPlaneCommandKind.STOP_COLLECTION_RUN:
            return await self.runner.stop_collection_run(command)
        if command.command is ControlPlaneCommandKind.TRIAL_RUN_ADVANCED_RULE:
            return await self.runner.trial_run_advanced_rule(command)
        if command.command is ControlPlaneCommandKind.HEALTH_CHECK:
            return await self.runner.health_check(command)
        raise NotImplementedError(f"unsupported command: {command.command}")

