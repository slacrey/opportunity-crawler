from __future__ import annotations

from dataclasses import dataclass

from opportunity_crawler.shared.config import AppRole, RoleSettings


@dataclass(frozen=True)
class RuntimeBundle:
    role: AppRole
    settings: RoleSettings

