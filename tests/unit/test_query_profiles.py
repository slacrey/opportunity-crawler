from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.collection.query_profiles import build_query_profile


def test_basic_rule_keywords_and_regions_build_query_profile() -> None:
    profile = build_query_profile(
        {
            "regions": ["昆山", "太仓"],
            "demand_keywords": ["AI", "云平台"],
            "exclude_keywords": ["物业"],
        },
        days_back=7,
    )

    assert profile.queries == ["昆山 AI", "昆山 云平台", "太仓 AI", "太仓 云平台"]
    assert profile.exclude_keywords == ["物业"]
    assert profile.days_back == 7

