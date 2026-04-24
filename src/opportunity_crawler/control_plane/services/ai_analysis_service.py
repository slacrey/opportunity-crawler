from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AIAnalysisResult:
    extracted_facts: dict[str, Any]
    inferred_analysis: dict[str, Any]
    outreach: dict[str, Any]
    provider_metadata: dict[str, Any]


class AIAnalysisService:
    def __init__(self, *, provider_enabled: bool = False) -> None:
        self.provider_enabled = provider_enabled

    def analyze(self, candidate: dict[str, Any]) -> AIAnalysisResult:
        title = str(candidate.get("title") or "")
        raw_text = str(candidate.get("raw_text") or "")
        organization_name = candidate.get("organization_name")
        summary = title if len(title) <= 80 else f"{title[:77]}..."
        return AIAnalysisResult(
            extracted_facts={
                "title": title,
                "organization_name": organization_name,
                "region": candidate.get("region"),
                "industry": candidate.get("industry"),
                "project_stage": candidate.get("project_stage"),
                "budget_amount": candidate.get("budget_amount"),
                "contact_phone": None,
            },
            inferred_analysis={
                "summary": summary or raw_text[:80],
                "next_step": "人工复核后进入跟进",
                "confidence": "fallback",
            },
            outreach={
                "opening": _build_opening(title, organization_name),
                "contact_phone": None,
            },
            provider_metadata={
                "provider": "deterministic_fallback",
                "provider_enabled": self.provider_enabled,
            },
        )


def _build_opening(title: str, organization_name: Any) -> str:
    if organization_name:
        return f"您好，关注到{organization_name}的{title}，想进一步了解项目需求。"
    return f"您好，关注到{title}，想进一步了解项目需求。"

