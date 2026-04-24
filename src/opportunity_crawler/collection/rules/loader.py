from __future__ import annotations

from dataclasses import dataclass
import json
import sqlite3
from typing import Any


@dataclass(frozen=True)
class CollectionRules:
    basic: dict[str, Any]
    advanced: dict[str, Any]


def load_collection_rules(connection: sqlite3.Connection, *, source_id: int) -> CollectionRules:
    basic_row = connection.execute(
        """
        SELECT
            regions_json,
            industry_keywords_json,
            demand_keywords_json,
            exclude_keywords_json,
            frequency,
            digest_enabled,
            digest_score_threshold,
            updated_by,
            updated_at
        FROM source_basic_rules
        WHERE source_id = ?
        """,
        (source_id,),
    ).fetchone()
    if basic_row is None:
        raise KeyError(f"source basic rules not found: {source_id}")

    advanced_row = connection.execute(
        """
        SELECT
            version,
            status,
            adapter_mode,
            entry_url,
            login_mode,
            selectors_json,
            pagination_policy_json,
            normalization_mapping_json,
            attachment_policy_json,
            risk_patterns_json,
            rate_limit_policy_json,
            retry_policy_json,
            trial_run_snapshot_json
        FROM source_advanced_rule_versions
        WHERE source_id = ? AND status = 'active'
        ORDER BY version DESC
        LIMIT 1
        """,
        (source_id,),
    ).fetchone()
    if advanced_row is None:
        raise KeyError(f"active advanced rules not found: {source_id}")

    return CollectionRules(
        basic={
            "regions": _json_list(basic_row["regions_json"]),
            "industry_keywords": _json_list(basic_row["industry_keywords_json"]),
            "demand_keywords": _json_list(basic_row["demand_keywords_json"]),
            "exclude_keywords": _json_list(basic_row["exclude_keywords_json"]),
            "frequency": basic_row["frequency"],
            "digest_enabled": bool(basic_row["digest_enabled"]),
            "digest_score_threshold": int(basic_row["digest_score_threshold"]),
            "updated_by": basic_row["updated_by"],
            "updated_at": basic_row["updated_at"],
        },
        advanced={
            "version": int(advanced_row["version"]),
            "status": advanced_row["status"],
            "adapter_mode": advanced_row["adapter_mode"],
            "entry_url": advanced_row["entry_url"],
            "login_mode": advanced_row["login_mode"],
            "selectors": _json_object(advanced_row["selectors_json"]),
            "pagination_policy": _json_object(advanced_row["pagination_policy_json"]),
            "normalization_mapping": _json_object(advanced_row["normalization_mapping_json"]),
            "attachment_policy": _json_object(advanced_row["attachment_policy_json"]),
            "risk_patterns": _json_object(advanced_row["risk_patterns_json"]),
            "rate_limit_policy": _json_object(advanced_row["rate_limit_policy_json"]),
            "retry_policy": _json_object(advanced_row["retry_policy_json"]),
            "trial_run_snapshot": _json_object(advanced_row["trial_run_snapshot_json"]),
        },
    )


def _json_list(raw: str | None) -> list[Any]:
    value = _loads(raw, [])
    return value if isinstance(value, list) else []


def _json_object(raw: str | None) -> dict[str, Any]:
    value = _loads(raw, {})
    return value if isinstance(value, dict) else {}


def _loads(raw: str | None, default: Any) -> Any:
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default

