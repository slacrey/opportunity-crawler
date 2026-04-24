from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.collection.adapters.api_or_feed import ApiOrFeedAdapter
from opportunity_crawler.collection.adapters.attachment_document import AttachmentDocumentAdapter
from opportunity_crawler.collection.adapters.manual_import import ManualImportAdapter
from opportunity_crawler.collection.adapters.public_search_list_detail import PublicSearchListDetailAdapter
from opportunity_crawler.collection.adapters.spa_or_ajax_search import SpaOrAjaxSearchAdapter
from opportunity_crawler.shared.contracts.agent_protocol import CollectionCommandMessage


def test_public_source_adapter_collects_list_and_detail_fixtures() -> None:
    list_html = """
    <div class="result"><a href="/detail/1">昆山 AI 项目</a><span class="date">2026-04-24</span></div>
    <div class="result"><a href="/detail/2">太仓云平台</a><span class="date">2026-04-23</span></div>
    """
    detail_pages = {
        "https://example.test/detail/1": "<article class='content'>昆山 智慧城市 AI</article>",
        "https://example.test/detail/2": "<article class='content'>太仓 云平台 数字化</article>",
    }
    adapter = PublicSearchListDetailAdapter()

    result = adapter.collect_from_fixtures(
        list_html=list_html,
        detail_pages=detail_pages,
        base_url="https://example.test",
        selectors={
            "list_selector": ".result",
            "detail_link_selector": "a",
            "published_at_selector": ".date",
            "content_selector": ".content",
        },
    )

    assert result.item_count == 2
    assert result.rows[0]["raw_text"] == "昆山 智慧城市 AI"
    assert result.diagnostic_snapshot["pagination_stop_reason"] == "fixture_complete"


def test_public_source_adapter_collects_entry_and_details_from_browser_runtime() -> None:
    command = CollectionCommandMessage(
        message_type="collection_command",
        command="start_collection_run",
        command_id="cmd-public",
        run_id="run-public",
        source_id=1,
        rule_version=1,
        adapter_mode="public_search_list_detail",
        login_mode="not_required",
        rule_payload={
            "entry_url": "https://example.test/search",
            "selectors": {
                "list_selector": ".result",
                "detail_link_selector": "a",
                "published_at_selector": ".date",
                "content_selector": ".content",
            },
            "pagination_policy": {"max_items": 1},
        },
    )
    browser_runtime = FakeBrowserRuntime(
        {
            "https://example.test/search": """
                <div class="result"><a href="/detail/1">昆山 AI 项目</a><span class="date">2026-04-24</span></div>
                <div class="result"><a href="/detail/2">太仓云平台</a><span class="date">2026-04-23</span></div>
            """,
            "https://example.test/detail/1": "<article class='content'>昆山 智慧城市 AI</article>",
            "https://example.test/detail/2": "<article class='content'>太仓 云平台 数字化</article>",
        }
    )
    adapter = PublicSearchListDetailAdapter()

    result = adapter.collect({"command": command, "browser_runtime": browser_runtime})

    assert browser_runtime.opened_urls == ["https://example.test/search", "https://example.test/detail/1"]
    assert result.item_count == 1
    assert result.rows[0]["title"] == "昆山 AI 项目"
    assert result.rows[0]["url"] == "https://example.test/detail/1"
    assert result.rows[0]["published_at"] == "2026-04-24"
    assert result.rows[0]["raw_text"] == "昆山 智慧城市 AI"
    assert result.rows[0]["source_item_key"] == "https://example.test/detail/1"
    assert result.diagnostic_snapshot["entry_url"] == "https://example.test/search"
    assert result.diagnostic_snapshot["pagination_stop_reason"] == "max_items_reached"


def test_public_source_adapter_reports_empty_result_stop_reason() -> None:
    command = CollectionCommandMessage(
        message_type="collection_command",
        command="start_collection_run",
        command_id="cmd-empty",
        run_id="run-empty",
        source_id=1,
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
    adapter = PublicSearchListDetailAdapter()

    result = adapter.collect({"command": command, "browser_runtime": FakeBrowserRuntime({"https://example.test/search": ""})})

    assert result.item_count == 0
    assert result.diagnostic_snapshot["pagination_stop_reason"] == "empty_result"


def test_spa_or_ajax_adapter_collects_rendered_list_and_detail_from_browser_runtime() -> None:
    command = CollectionCommandMessage(
        message_type="collection_command",
        command="start_collection_run",
        command_id="cmd-spa",
        run_id="run-spa",
        source_id=1,
        rule_version=1,
        adapter_mode="spa_or_ajax_search",
        login_mode="not_required",
        rule_payload={
            "entry_url": "https://example.test/app/search",
            "selectors": {
                "list_selector": ".card",
                "detail_link_selector": "a",
                "content_selector": ".detail",
            },
        },
    )
    browser_runtime = FakeBrowserRuntime(
        {
            "https://example.test/app/search": "<div class='card'><a href='/app/detail/1'>SPA 结果</a></div>",
            "https://example.test/app/detail/1": "<main class='detail'>渲染后的详情正文</main>",
        }
    )

    result = SpaOrAjaxSearchAdapter().collect({"command": command, "browser_runtime": browser_runtime})

    assert result.item_count == 1
    assert result.rows[0]["title"] == "SPA 结果"
    assert result.rows[0]["raw_text"] == "渲染后的详情正文"
    assert result.diagnostic_snapshot["adapter_mode"] == "spa_or_ajax_search"


def test_api_or_feed_adapter_collects_json_rows_from_browser_runtime() -> None:
    command = CollectionCommandMessage(
        message_type="collection_command",
        command="start_collection_run",
        command_id="cmd-api",
        run_id="run-api",
        source_id=1,
        rule_version=1,
        adapter_mode="api_or_feed",
        login_mode="not_required",
        rule_payload={
            "entry_url": "https://example.test/api/notices",
            "normalization_mapping": {
                "title": "headline",
                "url": "link",
                "published_at": "date",
                "raw_text": "summary",
            },
            "pagination_policy": {"max_items": 1},
        },
    )
    browser_runtime = FakeBrowserRuntime(
        {
            "https://example.test/api/notices": """
            {"items": [
              {"id": "n1", "headline": "API 招标公告", "link": "https://example.test/n1", "date": "2026-04-24", "summary": "API 正文 1"},
              {"id": "n2", "headline": "API 中标公告", "link": "https://example.test/n2", "date": "2026-04-23", "summary": "API 正文 2"}
            ]}
            """
        }
    )

    result = ApiOrFeedAdapter().collect({"command": command, "browser_runtime": browser_runtime})

    assert result.item_count == 1
    assert result.rows[0]["title"] == "API 招标公告"
    assert result.rows[0]["url"] == "https://example.test/n1"
    assert result.rows[0]["published_at"] == "2026-04-24"
    assert result.rows[0]["raw_text"] == "API 正文 1"
    assert result.rows[0]["source_item_key"] == "n1"
    assert result.diagnostic_snapshot["adapter_mode"] == "api_or_feed"
    assert result.diagnostic_snapshot["pagination_stop_reason"] == "max_items_reached"


def test_api_or_feed_adapter_collects_rss_items_from_browser_runtime() -> None:
    command = CollectionCommandMessage(
        message_type="collection_command",
        command="start_collection_run",
        command_id="cmd-rss",
        run_id="run-rss",
        source_id=1,
        rule_version=1,
        adapter_mode="api_or_feed",
        login_mode="not_required",
        rule_payload={"entry_url": "https://example.test/rss.xml"},
    )
    browser_runtime = FakeBrowserRuntime(
        {
            "https://example.test/rss.xml": """
            <rss><channel>
              <item>
                <guid>rss-1</guid>
                <title>RSS 采购公告</title>
                <link>https://example.test/rss/1</link>
                <pubDate>2026-04-24</pubDate>
                <description>RSS 正文</description>
              </item>
            </channel></rss>
            """
        }
    )

    result = ApiOrFeedAdapter().collect({"command": command, "browser_runtime": browser_runtime})

    assert result.item_count == 1
    assert result.rows[0]["title"] == "RSS 采购公告"
    assert result.rows[0]["url"] == "https://example.test/rss/1"
    assert result.rows[0]["raw_text"] == "RSS 正文"
    assert result.rows[0]["source_item_key"] == "rss-1"


def test_attachment_document_adapter_collects_text_attachment_from_entry_page() -> None:
    command = CollectionCommandMessage(
        message_type="collection_command",
        command="start_collection_run",
        command_id="cmd-attachment",
        run_id="run-attachment",
        source_id=1,
        rule_version=1,
        adapter_mode="attachment_document",
        login_mode="not_required",
        rule_payload={
            "entry_url": "https://example.test/notice",
            "selectors": {
                "title_selector": "h1",
                "published_at_selector": ".date",
                "content_selector": ".summary",
            },
            "attachment_policy": {"attachment_selector": "a.file"},
        },
    )
    browser_runtime = FakeBrowserRuntime(
        {
            "https://example.test/notice": """
              <article>
                <h1>附件采购公告</h1>
                <span class="date">2026-04-24</span>
                <p class="summary">公告摘要</p>
                <a class="file" href="/files/spec.txt">招标文件.txt</a>
              </article>
            """,
            "https://example.test/files/spec.txt": "附件正文：AI 平台采购要求",
        }
    )

    result = AttachmentDocumentAdapter().collect({"command": command, "browser_runtime": browser_runtime})

    assert result.item_count == 1
    assert result.rows[0]["title"] == "附件采购公告"
    assert result.rows[0]["published_at"] == "2026-04-24"
    assert result.rows[0]["raw_text"] == "公告摘要\n\n附件正文：AI 平台采购要求"
    assert result.rows[0]["source_item_key"] == "https://example.test/files/spec.txt"
    assert result.rows[0]["attachments"] == [
        {
            "name": "招标文件.txt",
            "url": "https://example.test/files/spec.txt",
            "content_type": "text",
        }
    ]
    assert result.diagnostic_snapshot["adapter_mode"] == "attachment_document"


def test_manual_import_adapter_reports_no_automated_collection_without_payload() -> None:
    result = ManualImportAdapter().collect({"browser_runtime": object()})

    assert result.rows == []
    assert result.diagnostic_snapshot == {
        "adapter_mode": "manual_import",
        "collection_implementation": "manual_payload_required",
    }


class FakeBrowserRuntime:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.opened_urls: list[str] = []

    def fetch_html(self, url: str) -> str:
        self.opened_urls.append(url)
        return self.pages[url]
