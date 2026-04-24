from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QueryProfile:
    queries: list[str]
    exclude_keywords: list[str]
    days_back: int


def build_query_profile(basic_rules: dict[str, Any], *, days_back: int) -> QueryProfile:
    regions = _string_list(basic_rules.get("regions"))
    demand_keywords = _string_list(basic_rules.get("demand_keywords"))
    exclude_keywords = _string_list(basic_rules.get("exclude_keywords"))

    if regions and demand_keywords:
        queries = [f"{region} {keyword}" for region in regions for keyword in demand_keywords]
    else:
        queries = regions or demand_keywords

    return QueryProfile(queries=queries, exclude_keywords=exclude_keywords, days_back=days_back)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]

