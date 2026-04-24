from __future__ import annotations

from typing import Any

from opportunity_crawler.shared.domain.opportunity import OpportunityScoreInput, OpportunityScoreResult, score_opportunity


class ScoringService:
    def score_candidate(self, candidate: dict[str, Any]) -> OpportunityScoreResult:
        return score_opportunity(
            OpportunityScoreInput(
                region=candidate.get("region"),
                industry=candidate.get("industry"),
                project_stage=candidate.get("project_stage"),
                demand_text=candidate.get("raw_text") or candidate.get("body") or candidate.get("title"),
                budget_amount=candidate.get("budget_amount"),
                source_priority=str(candidate.get("source_priority") or "P3"),
            )
        )

