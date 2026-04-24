from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.collection.pagination import PaginationPolicy


def test_pagination_stops_at_max_pages() -> None:
    policy = PaginationPolicy(max_pages=2, max_items=50)

    assert policy.stop_reason(page_count=1, item_count=10) is None
    assert policy.stop_reason(page_count=2, item_count=10) == "max_pages_reached"

