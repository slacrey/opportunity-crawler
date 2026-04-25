from __future__ import annotations

import logging
import sys
from pathlib import Path
import asyncio

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.agent.app import CollectionAgentApp
from opportunity_crawler.shared.contracts.agent_protocol import CollectionEventKind


class FakeRunner:
    async def start_collection_run(self, command):
        return {
            "event_kind": CollectionEventKind.RUN_SUCCEEDED,
            "command_id": command.command_id,
            "run_id": command.run_id,
            "source_id": command.source_id,
            "adapter_mode": command.adapter_mode,
            "page_count": 1,
            "item_count": 0,
            "rows": [],
            "diagnostic_snapshot": {"empty": True},
        }

    async def open_source_session(self, command):
        return {
            "event_kind": CollectionEventKind.PAGE_OPENED,
            "command_id": command.command_id,
            "run_id": command.run_id,
            "source_id": command.source_id,
            "adapter_mode": command.adapter_mode,
            "diagnostic_snapshot": {"source_account_id": command.source_account_id},
        }


class FakeClient:
    def __init__(self) -> None:
        self.events = []

    async def send_collection_event(self, **payload):
        self.events.append(payload)


def test_agent_app_handles_start_collection_run_command() -> None:
    asyncio.run(_assert_agent_app_handles_start_collection_run_command())


def test_agent_app_handles_open_source_session_command() -> None:
    asyncio.run(_assert_agent_app_handles_open_source_session_command())


def test_agent_app_logs_collection_command_lifecycle(caplog) -> None:
    caplog.set_level(logging.INFO, logger="opportunity_crawler.agent.app")

    asyncio.run(_assert_agent_app_handles_start_collection_run_command())

    messages = [record.getMessage() for record in caplog.records]
    assert any("agent.command.received" in message and "command_id=cmd-1" in message for message in messages)
    assert any("agent.event.sending" in message and "event_kind=run_started" in message for message in messages)
    assert any("agent.command.handled" in message and "event_kind=run_succeeded" in message for message in messages)
    assert any("agent.event.sending" in message and "event_kind=run_succeeded" in message for message in messages)


async def _assert_agent_app_handles_start_collection_run_command() -> None:
    client = FakeClient()
    app = CollectionAgentApp(runner=FakeRunner(), client=client)

    await app.handle_command(
        {
            "message_type": "collection_command",
            "command": "start_collection_run",
            "command_id": "cmd-1",
            "run_id": "run-1",
            "source_id": 10,
            "rule_version": 1,
            "adapter_mode": "manual_import",
            "login_mode": "not_required",
        }
    )

    assert client.events[0]["event_kind"] is CollectionEventKind.RUN_STARTED
    assert client.events[0]["run_id"] == "run-1"
    assert client.events[1]["event_kind"] is CollectionEventKind.RUN_SUCCEEDED
    assert client.events[1]["run_id"] == "run-1"


async def _assert_agent_app_handles_open_source_session_command() -> None:
    client = FakeClient()
    app = CollectionAgentApp(runner=FakeRunner(), client=client)

    await app.handle_command(
        {
            "message_type": "collection_command",
            "command": "open_source_session",
            "command_id": "cmd-open",
            "run_id": None,
            "source_id": 10,
            "adapter_mode": "login_search_list_detail",
            "login_mode": "login_required",
            "source_account_id": 7,
        }
    )

    assert client.events == [
        {
            "event_kind": CollectionEventKind.PAGE_OPENED,
            "command_id": "cmd-open",
            "run_id": None,
            "source_id": 10,
            "adapter_mode": "login_search_list_detail",
            "diagnostic_snapshot": {"source_account_id": 7},
        }
    ]
