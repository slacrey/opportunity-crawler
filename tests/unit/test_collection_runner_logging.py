from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.agent.runtime.collection_runner import CollectionRunner
from opportunity_crawler.collection.adapters.base import CollectionResult
from opportunity_crawler.shared.contracts.agent_protocol import CollectionCommandMessage


def test_collection_runner_logs_adapter_collection_lifecycle(caplog) -> None:
    caplog.set_level(logging.INFO, logger="opportunity_crawler.agent.runtime.collection_runner")

    asyncio.run(_run_successful_collection())

    messages = [record.getMessage() for record in caplog.records]
    assert any("agent.collection.collect.start" in message and "run_id=run-log" in message for message in messages)
    assert any("agent.collection.collect.succeeded" in message and "item_count=1" in message for message in messages)
    assert any(
        "agent.collection.item.collected" in message
        and "run_id=run-log" in message
        and "item_index=1" in message
        and "title=log row" in message
        for message in messages
    )


def test_collection_runner_logs_item_failures(caplog) -> None:
    caplog.set_level(logging.INFO, logger="opportunity_crawler.agent.runtime.collection_runner")

    asyncio.run(_run_collection_with_item_failure())

    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "agent.collection.item.failed" in message
        and "run_id=run-failed-item" in message
        and "item_index=1" in message
        and "failure_kind=parse_failed" in message
        and "url=https://example.test/detail/1" in message
        for message in messages
    )


async def _run_successful_collection() -> None:
    runner = CollectionRunner(adapter_registry=FakeAdapterRegistry(FakeAdapter()), browser_runtime=object())
    command = CollectionCommandMessage(
        message_type="collection_command",
        command="start_collection_run",
        command_id="cmd-log",
        run_id="run-log",
        source_id=10,
        rule_version=1,
        adapter_mode="fake_adapter",
        login_mode="not_required",
    )

    result = await runner.start_collection_run(command)

    assert result["item_count"] == 1


async def _run_collection_with_item_failure() -> None:
    runner = CollectionRunner(
        adapter_registry=FakeAdapterRegistry(
            FakeAdapter(
                rows=[],
                item_failures=[
                    {
                        "url": "https://example.test/detail/1",
                        "failure_kind": "parse_failed",
                        "detail": "missing .content",
                    }
                ],
            )
        ),
        browser_runtime=object(),
    )
    command = CollectionCommandMessage(
        message_type="collection_command",
        command="start_collection_run",
        command_id="cmd-failed-item",
        run_id="run-failed-item",
        source_id=10,
        rule_version=1,
        adapter_mode="fake_adapter",
        login_mode="not_required",
    )

    result = await runner.start_collection_run(command)

    assert result["item_count"] == 0


class FakeAdapterRegistry:
    def __init__(self, adapter: "FakeAdapter") -> None:
        self.adapter = adapter

    def resolve(self, mode: str) -> "FakeAdapter":
        _ = mode
        return self.adapter


class FakeAdapter:
    mode = "fake_adapter"

    def __init__(
        self,
        *,
        rows: list[dict[str, object]] | None = None,
        item_failures: list[dict[str, object]] | None = None,
    ) -> None:
        self.rows = rows if rows is not None else [{"title": "log row", "raw_text": "body"}]
        self.item_failures = item_failures or []

    def collect(self, context: dict[str, object]) -> CollectionResult:
        _ = context
        return CollectionResult(
            rows=self.rows,
            item_failures=self.item_failures,
            page_count=1,
            diagnostic_snapshot={"adapter_mode": self.mode},
        )
