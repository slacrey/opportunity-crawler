from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.shared.domain.rules import RuleValidationError, validate_advanced_rule_config


def test_validate_advanced_rule_config_accepts_public_search_rule() -> None:
    config = validate_advanced_rule_config(
        {
            "adapter_mode": "public_search_list_detail",
            "entry_url": "https://example.test/search",
            "login_mode": "not_required",
            "selectors": {
                "list_selector": ".result",
                "detail_link_selector": "a",
                "content_selector": ".content",
            },
            "pagination_policy": {"max_pages": 3},
            "normalization_mapping": {"title": "title"},
            "risk_patterns": {"captcha": ["验证码"]},
            "rate_limit_policy": {"min_interval_seconds": 5},
        }
    )

    assert config.adapter_mode == "public_search_list_detail"
    assert config.pagination_policy["max_pages"] == 3


def test_validate_advanced_rule_config_rejects_unsupported_adapter_mode() -> None:
    try:
        validate_advanced_rule_config(
            {
                "adapter_mode": "bespoke_site_script",
                "entry_url": "https://example.test",
                "login_mode": "not_required",
            }
        )
    except RuleValidationError as exc:
        assert exc.errors == [
            {
                "field": "adapter_mode",
                "message": "Unsupported adapter mode: bespoke_site_script",
                "type": "unsupported_adapter_mode",
            }
        ]
    else:
        raise AssertionError("expected RuleValidationError")


def test_validate_advanced_rule_config_rejects_missing_selector_for_list_detail_mode() -> None:
    try:
        validate_advanced_rule_config(
            {
                "adapter_mode": "public_search_list_detail",
                "entry_url": "https://example.test",
                "login_mode": "not_required",
                "selectors": {"list_selector": ".result"},
            }
        )
    except RuleValidationError as exc:
        assert {
            "field": "selectors.detail_link_selector",
            "message": "Field required for public_search_list_detail",
            "type": "missing",
        } in exc.errors
        assert {
            "field": "selectors.content_selector",
            "message": "Field required for public_search_list_detail",
            "type": "missing",
        } in exc.errors
    else:
        raise AssertionError("expected RuleValidationError")
