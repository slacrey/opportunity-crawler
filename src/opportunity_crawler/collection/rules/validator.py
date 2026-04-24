from __future__ import annotations

from typing import Any

from opportunity_crawler.shared.domain.rules import AdvancedRuleConfig, validate_advanced_rule_config


def validate_rule_payload(payload: dict[str, Any]) -> AdvancedRuleConfig:
    return validate_advanced_rule_config(payload)

