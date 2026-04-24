from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.collection.rules.validator import validate_rule_payload


def test_collection_rule_validator_delegates_advanced_rule_validation() -> None:
    validated = validate_rule_payload(
        {
            "adapter_mode": "manual_import",
            "entry_url": "manual://wechat",
            "login_mode": "not_required",
        }
    )

    assert validated.adapter_mode == "manual_import"

