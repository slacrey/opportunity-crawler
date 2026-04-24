from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.control_plane.services.ai_analysis_service import AIAnalysisService


def test_ai_analysis_service_uses_deterministic_fallback_without_inventing_contact_phone() -> None:
    analysis = AIAnalysisService(provider_enabled=False).analyze(
        {
            "title": "昆山 AI 云平台采购意向",
            "organization_name": "昆山某单位",
            "region": "昆山",
            "raw_text": "项目正文未出现联系人或电话。",
        }
    )

    assert analysis.extracted_facts["contact_phone"] is None
    assert analysis.extracted_facts["organization_name"] == "昆山某单位"
    assert analysis.inferred_analysis["summary"].startswith("昆山 AI 云平台采购意向")
    assert analysis.provider_metadata["provider"] == "deterministic_fallback"

