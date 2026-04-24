from __future__ import annotations

from typing import Any

from opportunity_crawler.agent.runtime.session_manager import SourceSessionManager, SourceSessionOpenRequest
from opportunity_crawler.collection.adapters.base import CollectionResult
from opportunity_crawler.collection.adapters.registry import AdapterRegistry
from opportunity_crawler.shared.contracts.agent_protocol import CollectionCommandMessage, CollectionEventKind


class CollectionRunner:
    def __init__(
        self,
        *,
        adapter_registry: Any | None = None,
        browser_runtime: Any | None = None,
        session_manager: SourceSessionManager | None = None,
    ) -> None:
        self.adapter_registry = adapter_registry or AdapterRegistry.default()
        self.browser_runtime = browser_runtime
        self.session_manager = session_manager

    async def start_collection_run(self, command: CollectionCommandMessage) -> dict[str, Any]:
        try:
            adapter = self.adapter_registry.resolve(str(command.adapter_mode))
            context = self._collection_context(command)
            result = _collect_with_adapter(adapter, context)
        except Exception as exc:
            return {
                "event_kind": CollectionEventKind.RUN_FAILED,
                "command_id": command.command_id,
                "run_id": command.run_id,
                "source_id": command.source_id,
                "adapter_mode": command.adapter_mode,
                "failure_kind": exc.__class__.__name__,
                "detail": str(exc),
                "diagnostic_snapshot": {
                    "adapter_mode": command.adapter_mode,
                    "runner_stage": "adapter_collect",
                },
            }

        return {
            "event_kind": CollectionEventKind.RUN_SUCCEEDED,
            "command_id": command.command_id,
            "run_id": command.run_id,
            "source_id": command.source_id,
            "adapter_mode": command.adapter_mode,
            "page_count": result.page_count,
            "item_count": result.item_count,
            "rows": result.rows,
            "diagnostic_snapshot": result.diagnostic_snapshot,
        }

    def _collection_context(self, command: CollectionCommandMessage) -> dict[str, Any]:
        session = None
        if command.source_account_id is not None and self.session_manager is not None:
            existing = self.session_manager.get_session(command.source_account_id)
            if existing is None:
                session = self.session_manager.open_session(
                    SourceSessionOpenRequest(
                        source_account_id=command.source_account_id,
                        source_id=command.source_id,
                        command_id=command.command_id,
                    )
                )
            else:
                session = self.session_manager.keep_session(command.source_account_id)

        return {
            "command": command,
            "browser_runtime": self.browser_runtime,
            "source_session": session,
            "source_id": command.source_id,
            "run_id": command.run_id,
            "rule_version": command.rule_version,
            "adapter_mode": command.adapter_mode,
            "login_mode": command.login_mode,
            "deadline_at": command.deadline_at,
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
        try:
            adapter = self.adapter_registry.resolve(str(command.adapter_mode))
            context = self._collection_context(command)
            result = _collect_with_adapter(adapter, context)
        except Exception as exc:
            return {
                "event_kind": CollectionEventKind.RUN_FAILED,
                "command_id": command.command_id,
                "run_id": command.run_id,
                "source_id": command.source_id,
                "adapter_mode": command.adapter_mode,
                "failure_kind": exc.__class__.__name__,
                "detail": str(exc),
                "diagnostic_snapshot": {
                    "adapter_mode": command.adapter_mode,
                    "trial_run": True,
                    "runner_stage": "adapter_collect",
                },
            }

        max_items = _positive_int(command.max_items)
        rows = result.rows[:max_items] if max_items is not None else result.rows
        diagnostic_snapshot = {
            **result.diagnostic_snapshot,
            "trial_run": True,
            "max_items": command.max_items,
            "preview_item_count": len(rows),
        }
        return {
            "event_kind": CollectionEventKind.TRIAL_RUN_COMPLETED,
            "command_id": command.command_id,
            "run_id": command.run_id,
            "source_id": command.source_id,
            "adapter_mode": command.adapter_mode,
            "page_count": result.page_count,
            "item_count": len(rows),
            "rows": rows,
            "diagnostic_snapshot": diagnostic_snapshot,
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


def _collect_with_adapter(adapter: Any, context: dict[str, Any]) -> CollectionResult:
    collect = getattr(adapter, "collect", None)
    if not callable(collect):
        raise NotImplementedError(f"adapter does not implement collect: {getattr(adapter, 'mode', 'unknown')}")
    result = collect(context)
    if not isinstance(result, CollectionResult):
        raise TypeError("adapter collect must return CollectionResult")
    return result


def _positive_int(value: object) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None
