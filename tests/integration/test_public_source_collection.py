from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.collection.adapters.public_search_list_detail import PublicSearchListDetailAdapter


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

