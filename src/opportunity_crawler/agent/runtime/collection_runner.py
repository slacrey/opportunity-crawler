from __future__ import annotations

from typing import Any

from opportunity_crawler.shared.contracts.agent_protocol import CollectionCommandMessage, CollectionEventKind


class CollectionRunner:
    async def start_collection_run(self, command: CollectionCommandMessage) -> dict[str, Any]:
        return {
            "event_kind": CollectionEventKind.RUN_SUCCEEDED,
            "command_id": command.command_id,
            "run_id": command.run_id,
            "source_id": command.source_id,
            "adapter_mode": command.adapter_mode,
            "page_count": 0,
            "item_count": 0,
            "rows": [],
            "diagnostic_snapshot": {"empty_result": True},
        }

    async def stop_collection_run(self, command: CollectionCommandMessage) -> dict[str, Any]:
        return {
            "event_kind": CollectionEventKind.RUN_STOPPED,
            "command_id": command.command_id,
            "run_id": command.run_id,
            "source_id": command.source_id,
            "adapter_mode": command.adapter_mode,
            "detail": command.reason,
        }

    async def trial_run_advanced_rule(self, command: CollectionCommandMessage) -> dict[str, Any]:
        return {
            "event_kind": CollectionEventKind.TRIAL_RUN_COMPLETED,
            "command_id": command.command_id,
            "run_id": command.run_id,
            "source_id": command.source_id,
            "adapter_mode": command.adapter_mode,
            "page_count": 0,
            "item_count": 0,
            "rows": [],
            "diagnostic_snapshot": {"trial_run": True, "max_items": command.max_items},
        }

    async def health_check(self, command: CollectionCommandMessage) -> dict[str, Any]:
        return {
            "event_kind": CollectionEventKind.HEALTH_CHECK_COMPLETED,
            "command_id": command.command_id,
            "run_id": command.run_id,
            "source_id": command.source_id,
            "adapter_mode": command.adapter_mode,
            "diagnostic_snapshot": {"browser_runtime": "available"},
        }

