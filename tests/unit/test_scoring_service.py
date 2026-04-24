from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.control_plane.services.scoring_service import ScoringService


def test_scoring_service_scores_target_region_industry_and_demand_text() -> None:
    scoring = ScoringService().score_candidate(
        {
            "region": "昆山",
            "industry": "制造业",
            "project_stage": "采购意向",
            "raw_text": "智慧城市 AI 云平台 数据中台 数字化转型",
            "budget_amount": 5000000,
            "source_priority": "P0",
        }
    )

    assert scoring.score >= 85
    assert scoring.priority_label in {"P0", "P1"}
    assert scoring.reasons

