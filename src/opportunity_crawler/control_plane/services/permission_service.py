from __future__ import annotations


class PermissionService:
    ROLE_PERMISSIONS: dict[str, set[str]] = {
        "operator": {
            "source:read",
            "source.basic_rules:update",
            "collection_runs:manage",
            "agents:read",
        },
        "business_manager": {
            "source:read",
            "source.basic_rules:update",
            "opportunities:review",
            "opportunities:write",
        },
        "manager": {
            "source:read",
            "opportunities:read",
            "goals:read",
            "notifications:read",
        },
        "administrator": {"*"},
    }

    def has_permission(self, roles: list[str] | tuple[str, ...], permission: str) -> bool:
        for role in roles:
            permissions = self.ROLE_PERMISSIONS.get(role, set())
            if "*" in permissions or permission in permissions:
                return True
        return False

