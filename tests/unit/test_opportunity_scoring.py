from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.shared.domain.opportunity import OpportunityScoreInput, score_opportunity


def test_score_opportunity_is_deterministic_and_explainable_for_target_match() -> None:
    result = score_opportunity(
        OpportunityScoreInput(
            region="昆山",
            industry="制造业",
            project_stage="采购意向",
            demand_text="智慧城市 AI 云平台 数字化转型",
            budget_amount=5_000_000,
            source_priority="P0",
        )
    )

    assert result.score >= 85
    assert result.priority_label == "P0"
    assert "region" in result.reasons
    assert "demand_keywords" in result.reasons


def test_score_opportunity_keeps_low_relevance_candidates_reviewable() -> None:
    result = score_opportunity(
        OpportunityScoreInput(
            region="外地",
            industry="其他",
            project_stage="未知",
            demand_text="普通新闻",
            budget_amount=None,
            source_priority="P2",
        )
    )

    assert result.score < 45
    assert result.priority_label == "P3"
    assert result.reasons["source_priority"] == "P2"
