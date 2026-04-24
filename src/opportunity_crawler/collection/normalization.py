from __future__ import annotations

from typing import Any


def apply_normalization_mapping(source: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for target_field, source_field in mapping.items():
        if source_field in source:
            normalized[target_field] = source[source_field]
    return normalized

