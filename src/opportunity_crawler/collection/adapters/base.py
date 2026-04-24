from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CollectionResult:
    rows: list[dict[str, Any]]
    diagnostic_snapshot: dict[str, Any] = field(default_factory=dict)
    page_count: int = 0
    item_failures: list[dict[str, Any]] = field(default_factory=list)

    @property
    def item_count(self) -> int:
        return len(self.rows)


class BaseAdapter:
    mode: str

