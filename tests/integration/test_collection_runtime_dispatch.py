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
import opportunity_crawler.agent.browser.camoufox_runtime as camoufox_runtime
from opportunity_crawler.agent.browser.camoufox_runtime import CamoufoxRuntime
from opportunity_crawler.agent.app import CollectionAgentApp
from opportunity_crawler.agent.runtime.collection_runner import CollectionRunner
from opportunity_crawler.agent.runtime.session_manager import SourceSessionManager
from opportunity_crawler.shared.contracts.agent_protocol import (
    CollectionEventKind,
    CollectionEventMessage,
    CollectionCommandMessage,
)
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
        assert command["rule_payload"]["query_profile"]["queries"][:3] == ["昆山 智能化", "昆山 弱电", "昆山 数字化"]
        assert command["rule_payload"]["basic_rules"]["regions"][0] == "昆山"

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


def test_control_panel_run_command_agent_browser_search_and_uploads_evidence(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    headers = auth_headers(client)
    source_id = first_source_id(client, headers)

    with client.websocket_connect("/api/agents/ws") as websocket:
        websocket.send_json(
            {
                "message_type": "register",
                "agent_id": "agent-browser",
                "host_id": "host-browser",
                "hostname": "localhost",
                "platform": "darwin",
                "app_version": "0.1.0",
                "capacity": 1,
            }
        )
        assert websocket.receive_json()["message_type"] == "registered"

        response = client.post(f"/api/sources/{source_id}/collection-runs", headers=headers)
        assert response.status_code == 201, response.text
        run = response.json()["run"]
        command = websocket.receive_json()

        browser_runtime = FakeSearchBrowserRuntime(
            search_pages={
                ("https://www.ccgp.gov.cn", "昆山 智能化"): """
                    <div class="result"><a href="/notice/1">昆山智能化采购公告</a></div>
                """,
            },
            detail_pages={
                "https://www.ccgp.gov.cn/notice/1": "<article class='content'>昆山 智能化 AI 云平台采购正文</article>",
            },
        )
        app = CollectionAgentApp(runner=CollectionRunner(browser_runtime=browser_runtime))
        result = asyncio.run(app.handle_command(command))

        websocket.send_json(CollectionEventMessage(**result).model_dump(mode="json"))
        assert websocket.receive_json() == {
            "message_type": "collection_event_ack",
            "event_kind": "run_succeeded",
            "run_id": run["run_id"],
        }

    with connect_sqlite(client.app.state.database_path) as connection:
        stored_run = connection.execute("SELECT * FROM collection_runs WHERE run_id = ?", (run["run_id"],)).fetchone()
        evidence = connection.execute("SELECT * FROM raw_evidence_items WHERE run_id = ?", (run["run_id"],)).fetchone()

    assert browser_runtime.submitted_searches[0] == ("https://www.ccgp.gov.cn", "昆山 智能化")
    assert stored_run["status"] == "succeeded"
    assert evidence["title"] == "昆山智能化采购公告"
    assert evidence["raw_text"] == "昆山 智能化 AI 云平台采购正文"


def test_collection_runner_returns_trial_run_preview_without_persistence() -> None:
    asyncio.run(_assert_collection_runner_returns_trial_run_preview_without_persistence())


def test_collection_runner_invokes_adapter_with_browser_context() -> None:
    asyncio.run(_assert_collection_runner_invokes_adapter_with_browser_context())


def test_collection_runner_opens_and_releases_source_session_commands() -> None:
    asyncio.run(_assert_collection_runner_opens_and_releases_source_session_commands())


def test_collection_runner_public_fetch_falls_back_when_browser_runtime_is_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    asyncio.run(_assert_collection_runner_public_fetch_falls_back_when_browser_runtime_is_unavailable(tmp_path, monkeypatch))


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


async def _assert_collection_runner_opens_and_releases_source_session_commands() -> None:
    browser_runtime = FakeBrowserRuntime()
    runner = CollectionRunner(
        adapter_registry=FakeAdapterRegistry(FakeAdapter()),
        browser_runtime=browser_runtime,
        session_manager=SourceSessionManager(browser_runtime),
    )
    open_command = CollectionCommandMessage(
        message_type="collection_command",
        command="open_source_session",
        command_id="cmd-open",
        run_id=None,
        source_id=10,
        adapter_mode="login_search_list_detail",
        login_mode="login_required",
        source_account_id=7,
    )

    opened = await runner.open_source_session(open_command)

    assert browser_runtime.opened_source_account_ids == [7]
    assert opened["event_kind"] is CollectionEventKind.PAGE_OPENED
    assert opened["command_id"] == "cmd-open"
    assert opened["source_id"] == 10
    assert opened["diagnostic_snapshot"]["source_account_id"] == 7
    assert opened["diagnostic_snapshot"]["session_id"] == "source-account-7"

    release_command = CollectionCommandMessage(
        message_type="collection_command",
        command="release_source_session",
        command_id="cmd-release",
        run_id=None,
        source_id=10,
        adapter_mode="login_search_list_detail",
        login_mode="login_required",
        source_account_id=7,
    )

    released = await runner.release_source_session(release_command)

    assert browser_runtime.closed_session_ids == ["source-account-7"]
    assert released["event_kind"] is CollectionEventKind.RUN_STOPPED
    assert released["diagnostic_snapshot"]["source_account_id"] == 7
    assert released["diagnostic_snapshot"]["released"] is True


async def _assert_collection_runner_public_fetch_falls_back_when_browser_runtime_is_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pages = {
        "https://example.test/search": """
            <div class="result"><a href="/detail/1">昆山 AI 项目</a></div>
        """,
        "https://example.test/detail/1": "<article class='content'>昆山 智慧城市 AI</article>",
    }

    def browser_factory(profile_path: Path) -> object:
        _ = profile_path
        raise RuntimeError("camoufox unavailable")

    def urllib_fetcher(url: str) -> str:
        return pages[url]

    monkeypatch.setattr(camoufox_runtime, "_fetch_html_with_urllib", urllib_fetcher)
    runner = CollectionRunner(
        browser_runtime=CamoufoxRuntime(browser_profiles_dir=tmp_path, browser_factory=browser_factory),
    )
    command = CollectionCommandMessage(
        message_type="collection_command",
        command="start_collection_run",
        command_id="cmd-public-fallback",
        run_id="run-public-fallback",
        source_id=10,
        rule_version=1,
        adapter_mode="public_search_list_detail",
        login_mode="not_required",
        rule_payload={
            "entry_url": "https://example.test/search",
            "selectors": {
                "list_selector": ".result",
                "detail_link_selector": "a",
                "content_selector": ".content",
            },
        },
    )

    result = await runner.start_collection_run(command)

    assert result["event_kind"] is CollectionEventKind.RUN_SUCCEEDED
    assert result["rows"][0]["title"] == "昆山 AI 项目"
    assert result["rows"][0]["raw_text"] == "昆山 智慧城市 AI"


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


class FakeBrowserRuntime:
    def __init__(self) -> None:
        self.opened_source_account_ids: list[int] = []
        self.closed_session_ids: list[str] = []

    def open_session(self, request) -> dict[str, str]:
        self.opened_source_account_ids.append(request.source_account_id)
        return {"session_id": f"source-account-{request.source_account_id}"}

    def ensure_session_alive(self, session_id: str) -> None:
        return None

    def close_session(self, session_id: str) -> None:
        self.closed_session_ids.append(session_id)

    def clear_source_account_state(self, source_account_id: int) -> None:
        return None


class FakeSearchBrowserRuntime:
    def __init__(
        self,
        *,
        search_pages: dict[tuple[str, str], str],
        detail_pages: dict[str, str],
    ) -> None:
        self.search_pages = search_pages
        self.detail_pages = detail_pages
        self.submitted_searches: list[tuple[str, str]] = []
        self.opened_urls: list[str] = []

    def submit_search(self, entry_url: str, query: str, **kwargs: object) -> str:
        _ = kwargs
        self.submitted_searches.append((entry_url, query))
        return self.search_pages.get((entry_url, query), "")

    def fetch_html(self, url: str) -> str:
        self.opened_urls.append(url)
        return self.detail_pages[url]
