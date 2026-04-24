from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.collection.parsing import parse_list_items


def test_parse_list_items_extracts_titles_links_and_dates_from_fixture_html() -> None:
    html = """
    <div class="result"><a href="/a">昆山 AI 项目</a><span class="date">2026-04-24</span></div>
    <div class="result"><a href="https://example.test/b">太仓云平台</a><span class="date">2026-04-23</span></div>
    """

    rows = parse_list_items(
        html,
        selectors={
            "list_selector": ".result",
            "detail_link_selector": "a",
            "published_at_selector": ".date",
        },
        base_url="https://example.test",
    )

    assert rows[0]["title"] == "昆山 AI 项目"
    assert rows[0]["url"] == "https://example.test/a"
    assert rows[1]["published_at"] == "2026-04-23"

