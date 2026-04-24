from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OpportunityScoreInput:
    region: str | None
    industry: str | None
    project_stage: str | None
    demand_text: str | None
    budget_amount: float | None
    source_priority: str


@dataclass(frozen=True)
class OpportunityScoreResult:
    score: int
    priority_label: str
    reasons: dict[str, object]


TARGET_REGIONS = ("昆山", "太仓", "常熟", "张家港", "苏州")
TARGET_INDUSTRIES = ("四新", "政府", "医疗", "教育", "金融", "制造")
TARGET_STAGES = ("规划", "土建", "建设", "设计", "采购意向", "招标计划")
DEMAND_KEYWORDS = ("数字化", "AI", "人工智能", "云平台", "云计算", "智慧城市", "弱电", "数据中台")
SOURCE_PRIORITY_POINTS = {"P0": 5, "P1": 4, "P2": 2, "P3": 0}


def score_opportunity(candidate: OpportunityScoreInput) -> OpportunityScoreResult:
    score = 0
    reasons: dict[str, object] = {"source_priority": candidate.source_priority}

    region = candidate.region or ""
    matched_regions = [item for item in TARGET_REGIONS if item in region]
    if matched_regions:
        score += 25
        reasons["region"] = matched_regions

    industry = candidate.industry or ""
    matched_industries = [item for item in TARGET_INDUSTRIES if item in industry]
    if matched_industries:
        score += 20
        reasons["industry"] = matched_industries

    stage = candidate.project_stage or ""
    matched_stages = [item for item in TARGET_STAGES if item in stage]
    if matched_stages:
        score += 15
        reasons["project_stage"] = matched_stages

    demand_text = candidate.demand_text or ""
    matched_keywords = [item for item in DEMAND_KEYWORDS if item.lower() in demand_text.lower()]
    if matched_keywords:
        score += min(20, len(matched_keywords) * 7)
        reasons["demand_keywords"] = matched_keywords

    if candidate.budget_amount is not None and candidate.budget_amount > 0:
        score += 15
        reasons["budget"] = "present"

    score += SOURCE_PRIORITY_POINTS.get(candidate.source_priority, 0)
    score = min(score, 100)

    if score >= 85:
        priority_label = "P0"
    elif score >= 70:
        priority_label = "P1"
    elif score >= 45:
        priority_label = "P2"
    else:
        priority_label = "P3"

    return OpportunityScoreResult(score=score, priority_label=priority_label, reasons=reasons)

