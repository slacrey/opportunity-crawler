from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.integrations.dingtalk import DingTalkDigestBuilder


def test_dingtalk_digest_masks_sensitive_contact_fields() -> None:
    message = DingTalkDigestBuilder().build_daily_digest(
        [
            {
                "title": "昆山 AI 项目",
                "score": 92,
                "priority_label": "P0",
                "organization_name": "昆山某单位",
                "contact_phone": "13812340000",
            }
        ]
    )

    assert "昆山 AI 项目" in message
    assert "138****0000" in message
    assert "13812340000" not in message

