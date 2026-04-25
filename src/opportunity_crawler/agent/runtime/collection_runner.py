from __future__ import annotations

import logging
from typing import Any

from opportunity_crawler.agent.runtime.session_manager import SourceSessionManager, SourceSessionOpenRequest
from opportunity_crawler.collection.adapters.base import CollectionResult
from opportunity_crawler.collection.adapters.registry import AdapterRegistry
from opportunity_crawler.shared.contracts.agent_protocol import CollectionCommandMessage, CollectionEventKind


logger = logging.getLogger(__name__)


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
        logger.info(
            "agent.collection.collect.start command_id=%s run_id=%s source_id=%s adapter_mode=%s rule_version=%s",
            command.command_id,
            command.run_id,
            command.source_id,
            command.adapter_mode,
            command.rule_version,
        )
        try:
            adapter = self.adapter_registry.resolve(str(command.adapter_mode))
            context = self._collection_context(command)
            result = _collect_with_adapter(adapter, context)
        except Exception as exc:
            logger.exception(
                "agent.collection.collect.failed command_id=%s run_id=%s source_id=%s adapter_mode=%s failure_kind=%s",
                command.command_id,
                command.run_id,
                command.source_id,
                command.adapter_mode,
                exc.__class__.__name__,
            )
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

        logger.info(
            "agent.collection.collect.succeeded command_id=%s run_id=%s source_id=%s adapter_mode=%s page_count=%s item_count=%s",
            command.command_id,
            command.run_id,
            command.source_id,
            command.adapter_mode,
            result.page_count,
            result.item_count,
        )
        _log_collected_items(command=command, rows=result.rows)
        _log_item_failures(command=command, item_failures=result.item_failures)
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
                        initial_url=_entry_url(command),
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

    async def open_source_session(self, command: CollectionCommandMessage) -> dict[str, Any]:
        logger.info(
            "agent.source_session.open.start command_id=%s source_id=%s source_account_id=%s adapter_mode=%s",
            command.command_id,
            command.source_id,
            command.source_account_id,
            command.adapter_mode,
        )
        try:
            source_account_id = _required_source_account_id(command)
            manager = self._required_session_manager()
            existing = manager.get_session(source_account_id)
            if existing is None:
                session = manager.open_session(
                    SourceSessionOpenRequest(
                        source_account_id=source_account_id,
                        source_id=command.source_id,
                        command_id=command.command_id,
                        initial_url=_entry_url(command),
                    )
                )
                reused = False
            else:
                session = manager.keep_session(source_account_id)
                reused = True
        except Exception as exc:
            logger.exception(
                "agent.source_session.open.failed command_id=%s source_id=%s source_account_id=%s failure_kind=%s",
                command.command_id,
                command.source_id,
                command.source_account_id,
                exc.__class__.__name__,
            )
            return _failed_command_result(command, exc, runner_stage="source_session_open")

        snapshot = _session_diagnostic_snapshot(session)
        snapshot.update({"source_account_id": source_account_id, "session_reused": reused})
        logger.info(
            "agent.source_session.open.succeeded command_id=%s source_id=%s source_account_id=%s session_id=%s reused=%s",
            command.command_id,
            command.source_id,
            source_account_id,
            snapshot.get("session_id"),
            reused,
        )
        return {
            "event_kind": CollectionEventKind.PAGE_OPENED,
            "command_id": command.command_id,
            "run_id": command.run_id,
            "source_id": command.source_id,
            "adapter_mode": command.adapter_mode,
            "diagnostic_snapshot": snapshot,
        }

    async def release_source_session(self, command: CollectionCommandMessage) -> dict[str, Any]:
        logger.info(
            "agent.source_session.release.start command_id=%s source_id=%s source_account_id=%s adapter_mode=%s",
            command.command_id,
            command.source_id,
            command.source_account_id,
            command.adapter_mode,
        )
        try:
            source_account_id = _required_source_account_id(command)
            released = self._required_session_manager().release_session(source_account_id)
        except Exception as exc:
            logger.exception(
                "agent.source_session.release.failed command_id=%s source_id=%s source_account_id=%s failure_kind=%s",
                command.command_id,
                command.source_id,
                command.source_account_id,
                exc.__class__.__name__,
            )
            return _failed_command_result(command, exc, runner_stage="source_session_release")

        snapshot = _session_diagnostic_snapshot(released) if released is not None else {}
        snapshot.update({"source_account_id": source_account_id, "released": released is not None})
        logger.info(
            "agent.source_session.release.succeeded command_id=%s source_id=%s source_account_id=%s released=%s",
            command.command_id,
            command.source_id,
            source_account_id,
            released is not None,
        )
        return {
            "event_kind": CollectionEventKind.RUN_STOPPED,
            "command_id": command.command_id,
            "run_id": command.run_id,
            "source_id": command.source_id,
            "adapter_mode": command.adapter_mode,
            "detail": "source session released" if released is not None else "source session was not active",
            "diagnostic_snapshot": snapshot,
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
        logger.info(
            "agent.collection.trial.start command_id=%s run_id=%s source_id=%s adapter_mode=%s rule_version=%s max_items=%s",
            command.command_id,
            command.run_id,
            command.source_id,
            command.adapter_mode,
            command.rule_version,
            command.max_items,
        )
        try:
            adapter = self.adapter_registry.resolve(str(command.adapter_mode))
            context = self._collection_context(command)
            result = _collect_with_adapter(adapter, context)
        except Exception as exc:
            logger.exception(
                "agent.collection.trial.failed command_id=%s run_id=%s source_id=%s adapter_mode=%s failure_kind=%s",
                command.command_id,
                command.run_id,
                command.source_id,
                command.adapter_mode,
                exc.__class__.__name__,
            )
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
        logger.info(
            "agent.collection.trial.succeeded command_id=%s run_id=%s source_id=%s adapter_mode=%s page_count=%s preview_item_count=%s",
            command.command_id,
            command.run_id,
            command.source_id,
            command.adapter_mode,
            result.page_count,
            len(rows),
        )
        _log_collected_items(command=command, rows=rows, trial_run=True)
        _log_item_failures(command=command, item_failures=result.item_failures, trial_run=True)
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

    def _required_session_manager(self) -> SourceSessionManager:
        if self.session_manager is None:
            raise RuntimeError("source session manager is not configured")
        return self.session_manager


def _collect_with_adapter(adapter: Any, context: dict[str, Any]) -> CollectionResult:
    collect = getattr(adapter, "collect", None)
    if not callable(collect):
        raise NotImplementedError(f"adapter does not implement collect: {getattr(adapter, 'mode', 'unknown')}")
    result = collect(context)
    if not isinstance(result, CollectionResult):
        raise TypeError("adapter collect must return CollectionResult")
    return result


def _failed_command_result(
    command: CollectionCommandMessage,
    exc: Exception,
    *,
    runner_stage: str,
) -> dict[str, Any]:
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
            "runner_stage": runner_stage,
        },
    }


def _required_source_account_id(command: CollectionCommandMessage) -> int:
    if command.source_account_id is None:
        raise ValueError("source_account_id is required")
    return command.source_account_id


def _entry_url(command: CollectionCommandMessage) -> str | None:
    payload = command.rule_payload or command.draft_rule_payload or {}
    value = payload.get("entry_url")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _session_diagnostic_snapshot(session: Any) -> dict[str, Any]:
    return {
        "session_id": _session_value(session, "session_id"),
        "profile_path": _session_value(session, "profile_path"),
    }


def _session_value(session: Any, key: str) -> Any:
    if session is None:
        return None
    if isinstance(session, dict):
        value = session.get(key)
    else:
        value = getattr(session, key, None)
    if value is None:
        return None
    return str(value) if key.endswith("_path") else value


def _log_collected_items(
    *,
    command: CollectionCommandMessage,
    rows: list[dict[str, Any]],
    trial_run: bool = False,
) -> None:
    if not rows:
        logger.info(
            "agent.collection.item.none command_id=%s run_id=%s source_id=%s adapter_mode=%s trial_run=%s",
            command.command_id,
            command.run_id,
            command.source_id,
            command.adapter_mode,
            trial_run,
        )
        return

    for index, row in enumerate(rows, start=1):
        logger.info(
            "agent.collection.item.collected command_id=%s run_id=%s source_id=%s adapter_mode=%s trial_run=%s item_index=%s title=%s url=%s source_item_key=%s published_at=%s raw_text_length=%s",
            command.command_id,
            command.run_id,
            command.source_id,
            command.adapter_mode,
            trial_run,
            index,
            _log_value(row.get("title")),
            _log_value(row.get("url")),
            _log_value(row.get("source_item_key")),
            _log_value(row.get("published_at")),
            len(str(row.get("raw_text") or "")),
        )


def _log_item_failures(
    *,
    command: CollectionCommandMessage,
    item_failures: list[dict[str, Any]],
    trial_run: bool = False,
) -> None:
    for index, failure in enumerate(item_failures, start=1):
        logger.info(
            "agent.collection.item.failed command_id=%s run_id=%s source_id=%s adapter_mode=%s trial_run=%s item_index=%s url=%s failure_kind=%s detail=%s",
            command.command_id,
            command.run_id,
            command.source_id,
            command.adapter_mode,
            trial_run,
            index,
            _log_value(failure.get("url")),
            _log_value(failure.get("failure_kind")),
            _log_value(failure.get("detail")),
        )


def _log_value(value: Any) -> str:
    if value is None:
        return "-"
    text = str(value).replace("\n", " ").strip()
    return text[:160] if len(text) > 160 else text


def _positive_int(value: object) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None
