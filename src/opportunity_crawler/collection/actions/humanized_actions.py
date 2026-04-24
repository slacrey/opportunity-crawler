from __future__ import annotations

from dataclasses import dataclass
from random import Random


@dataclass(frozen=True)
class HumanizedDelayPolicy:
    min_seconds: float = 0.8
    max_seconds: float = 2.5

    def next_delay(self, random: Random | None = None) -> float:
        source = random or Random()
        return source.uniform(self.min_seconds, self.max_seconds)


def normalize_query_text(value: str) -> str:
    return " ".join(value.split())

