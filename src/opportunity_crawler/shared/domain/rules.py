from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError


SUPPORTED_ADAPTER_MODES = {
    "public_search_list_detail",
    "public_channel_news",
    "login_search_list_detail",
    "spa_or_ajax_search",
    "attachment_document",
    "manual_import",
    "api_or_feed",
}

SUPPORTED_LOGIN_MODES = {"not_required", "login_required"}

_REQUIRED_SELECTORS_BY_MODE: dict[str, tuple[str, ...]] = {
    "public_search_list_detail": (
        "list_selector",
        "detail_link_selector",
        "content_selector",
    ),
    "login_search_list_detail": (
        "list_selector",
        "detail_link_selector",
        "content_selector",
    ),
    "public_channel_news": ("list_selector", "detail_link_selector", "content_selector"),
}


class AdvancedRuleConfig(BaseModel):
    adapter_mode: str
    entry_url: str
    login_mode: str
    selectors: dict[str, Any] = Field(default_factory=dict)
    pagination_policy: dict[str, Any] = Field(default_factory=dict)
    normalization_mapping: dict[str, Any] = Field(default_factory=dict)
    attachment_policy: dict[str, Any] = Field(default_factory=dict)
    risk_patterns: dict[str, Any] = Field(default_factory=dict)
    rate_limit_policy: dict[str, Any] = Field(default_factory=dict)
    retry_policy: dict[str, Any] = Field(default_factory=dict)


class RuleValidationError(Exception):
    def __init__(self, errors: list[dict[str, str]]) -> None:
        super().__init__("invalid advanced rule config")
        self.errors = errors


def validate_advanced_rule_config(payload: dict[str, Any]) -> AdvancedRuleConfig:
    try:
        config = AdvancedRuleConfig.model_validate(payload)
    except ValidationError as exc:
        raise RuleValidationError(_normalize_validation_errors(exc)) from exc

    errors: list[dict[str, str]] = []
    if config.adapter_mode not in SUPPORTED_ADAPTER_MODES:
        errors.append(
            {
                "field": "adapter_mode",
                "message": f"Unsupported adapter mode: {config.adapter_mode}",
                "type": "unsupported_adapter_mode",
            }
        )

    if config.login_mode not in SUPPORTED_LOGIN_MODES:
        errors.append(
            {
                "field": "login_mode",
                "message": f"Unsupported login mode: {config.login_mode}",
                "type": "unsupported_login_mode",
            }
        )

    for selector_name in _REQUIRED_SELECTORS_BY_MODE.get(config.adapter_mode, ()):
        if not config.selectors.get(selector_name):
            errors.append(
                {
                    "field": f"selectors.{selector_name}",
                    "message": f"Field required for {config.adapter_mode}",
                    "type": "missing",
                }
            )

    if errors:
        raise RuleValidationError(errors)

    return config


def _normalize_validation_errors(exc: ValidationError) -> list[dict[str, str]]:
    return [
        {
            "field": ".".join(str(part) for part in issue["loc"]),
            "message": str(issue["msg"]),
            "type": str(issue["type"]),
        }
        for issue in exc.errors()
    ]

