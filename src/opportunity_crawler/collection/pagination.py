from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PaginationPolicy:
    max_pages: int = 1
    max_items: int = 50

    def stop_reason(self, *, page_count: int, item_count: int) -> str | None:
        if page_count >= self.max_pages:
            return "max_pages_reached"
        if item_count >= self.max_items:
            return "max_items_reached"
        return None

