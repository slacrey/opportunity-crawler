from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.control_plane.services.permission_service import PermissionService


def test_permission_service_enforces_role_boundaries() -> None:
    permissions = PermissionService()

    assert permissions.has_permission(["business_manager"], "source.basic_rules:update")
    assert not permissions.has_permission(["business_manager"], "source.advanced_rules:update")
    assert permissions.has_permission(["administrator"], "source.advanced_rules:update")

