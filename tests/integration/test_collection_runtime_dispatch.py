from __future__ import annotations

import sys
from pathlib import Path
import asyncio

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tests.integration.api_helpers import auth_headers, build_client, first_source_id
from opportunity_crawler.collection.adapters.base import CollectionResult
from opportunity_crawler.agent.runtime.collection_runner import CollectionRunner
from opportunity_crawler.shared.contracts.agent_protocol import CollectionEventKind, CollectionCommandMessage
from opportunity_crawler.shared.db.base import connect_sqlite


def test_control_plane_dispatches_collection_run_and_persists_agent_events(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    headers = auth_headers(client)
    source_id = first_source_id(client, headers)

    with client.websocket_connect("/api/agents/ws") as websocket:
        websocket.send_json(
            {
                "message_type": "register",
                "agent_id": "agent-loop",
                "host_id": "host-loop",
                "hostname": "localhost",
                "platform": "darwin",
                "app_version": "0.1.0",
                "capacity": 1,
            }
        )
        registered = websocket.receive_json()
        assert registered["message_type"] == "registered"

        response = client.post(f"/api/sources/{source_id}/collection-runs", headers=headers)
        assert response.status_code == 201, response.text
        run = response.json()["run"]
        assert run["source_id"] == source_id
        assert run["agent_id"] == "agent-loop"
        assert run["status"] == "queued"

        command = websocket.receive_json()
        assert command["message_type"] == "collection_command"
        assert command["command"] == "start_collection_run"
        assert command["run_id"] == run["run_id"]
        assert command["source_id"] == source_id
        assert command["rule_payload"]["entry_url"] == "https://www.ccgp.gov.cn"
        assert command["rule_payload"]["selectors"]["list_selector"] == ".result"

        websocket.send_json(
            {
                "message_type": "collection_event",
                "event_kind": "run_started",
                "command_id": command["command_id"],
                "run_id": run["run_id"],
                "source_id": source_id,
                "adapter_mode": command["adapter_mode"],
            }
        )
        assert websocket.receive_json() == {
            "message_type": "collection_event_ack",
            "event_kind": "run_started",
            "run_id": run["run_id"],
        }

        websocket.send_json(
            {
                "message_type": "collection_event",
                "event_kind": "run_succeeded",
                "command_id": command["command_id"],
                "run_id": run["run_id"],
                "source_id": source_id,
                "adapter_mode": command["adapter_mode"],
                "page_count": 2,
                "item_count": 1,
                "rows": [
                    {
                        "source_item_key": "notice-1",
                        "url": "https://example.test/notices/1",
                        "title": "昆山 AI 云平台采购公告",
                        "published_at": "2026-04-24",
                        "raw_text": "昆山 制造业 AI 云平台 数字化转型采购公告",
                        "attachments": [{"name": "招标文件.pdf", "url": "https://example.test/a.pdf"}],
                    }
                ],
                "diagnostic_snapshot": {"stop_reason": "completed"},
            }
        )
        assert websocket.receive_json() == {
            "message_type": "collection_event_ack",
            "event_kind": "run_succeeded",
            "run_id": run["run_id"],
        }

    with connect_sqlite(client.app.state.database_path) as connection:
        stored_run = connection.execute(
            "SELECT * FROM collection_runs WHERE run_id = ?",
            (run["run_id"],),
        ).fetchone()
        evidence = connection.execute(
            "SELECT * FROM raw_evidence_items WHERE run_id = ?",
            (run["run_id"],),
        ).fetchone()

    assert stored_run["status"] == "succeeded"
    assert stored_run["page_count"] == 2
    assert stored_run["item_count"] == 1
    assert stored_run["finished_at"] is not None
    assert '"stop_reason": "completed"' in stored_run["diagnostic_snapshot_json"]
    assert evidence["source_id"] == source_id
    assert evidence["source_item_key"] == "notice-1"
    assert evidence["title"] == "昆山 AI 云平台采购公告"
    assert evidence["raw_text"] == "昆山 制造业 AI 云平台 数字化转型采购公告"
    assert "招标文件.pdf" in evidence["attachments_json"]
    assert evidence["content_fingerprint"]


def test_collection_runner_returns_trial_run_preview_without_persistence() -> None:
    asyncio.run(_assert_collection_runner_returns_trial_run_preview_without_persistence())


def test_collection_runner_invokes_adapter_with_browser_context() -> None:
    asyncio.run(_assert_collection_runner_invokes_adapter_with_browser_context())


async def _assert_collection_runner_returns_trial_run_preview_without_persistence() -> None:
    adapter = FakeAdapter(
        rows=[
            {"title": "试运行第一条", "raw_text": "正文 1"},
            {"title": "试运行第二条", "raw_text": "正文 2"},
        ]
    )
    registry = FakeAdapterRegistry(adapter)
    browser_runtime = object()
    runner = CollectionRunner(adapter_registry=registry, browser_runtime=browser_runtime)
    command = CollectionCommandMessage(
        message_type="collection_command",
        command="trial_run_advanced_rule",
        command_id="cmd-1",
        run_id="trial-1",
        source_id=10,
        rule_version=2,
        adapter_mode="fake_adapter",
        login_mode="not_required",
        draft_rule_payload={"entry_url": "https://example.test/search"},
        max_items=1,
    )

    result = await runner.trial_run_advanced_rule(command)

    assert registry.resolved_modes == ["fake_adapter"]
    assert adapter.contexts[0]["command"] is command
    assert adapter.contexts[0]["browser_runtime"] is browser_runtime
    assert result["event_kind"] is CollectionEventKind.TRIAL_RUN_COMPLETED
    assert result["rows"] == [{"title": "试运行第一条", "raw_text": "正文 1"}]
    assert result["item_count"] == 1
    assert result["diagnostic_snapshot"]["trial_run"] is True
    assert result["diagnostic_snapshot"]["adapter_mode"] == "fake_adapter"


async def _assert_collection_runner_invokes_adapter_with_browser_context() -> None:
    adapter = FakeAdapter()
    registry = FakeAdapterRegistry(adapter)
    browser_runtime = object()
    runner = CollectionRunner(adapter_registry=registry, browser_runtime=browser_runtime)
    command = CollectionCommandMessage(
        message_type="collection_command",
        command="start_collection_run",
        command_id="cmd-adapter",
        run_id="run-adapter",
        source_id=10,
        rule_version=1,
        adapter_mode="fake_adapter",
        login_mode="not_required",
    )

    result = await runner.start_collection_run(command)

    assert registry.resolved_modes == ["fake_adapter"]
    assert adapter.contexts[0]["command"] is command
    assert adapter.contexts[0]["browser_runtime"] is browser_runtime
    assert result["event_kind"] is CollectionEventKind.RUN_SUCCEEDED
    assert result["rows"] == [{"title": "适配器采集结果", "raw_text": "正文"}]
    assert result["diagnostic_snapshot"]["adapter_mode"] == "fake_adapter"


class FakeAdapterRegistry:
    def __init__(self, adapter: "FakeAdapter") -> None:
        self.adapter = adapter
        self.resolved_modes: list[str] = []

    def resolve(self, mode: str) -> "FakeAdapter":
        self.resolved_modes.append(mode)
        return self.adapter


class FakeAdapter:
    mode = "fake_adapter"

    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self.contexts: list[dict[str, object]] = []
        self.rows = rows or [{"title": "适配器采集结果", "raw_text": "正文"}]

    def collect(self, context: dict[str, object]) -> CollectionResult:
        self.contexts.append(context)
        return CollectionResult(
            rows=self.rows,
            page_count=1,
            diagnostic_snapshot={"adapter_mode": self.mode},
        )
