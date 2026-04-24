from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping
import os
import tomllib

from pydantic import BaseModel, Field, ValidationError


class AppRole(StrEnum):
    CONTROL_PLANE = "control_plane"
    AGENT = "agent"
    ALL_IN_ONE = "all_in_one"


class SharedSettings(BaseModel):
    environment: str = "development"
    data_dir: Path = Path("./var/data")
    log_dir: Path = Path("./var/logs")
    tmp_dir: Path = Path("./var/tmp")
    database_path: Path = Path("./var/data/opportunity-crawler.db")
    evidence_dir: Path = Path("./var/data/evidence")
    screenshots_dir: Path = Path("./var/data/screenshots")
    browser_profiles_dir: Path = Path("./var/data/browser-profiles")


class ControlPlaneSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    static_url_prefix: str = "/static"
    frontend_dist_dir: Path | None = None


class AgentSettings(BaseModel):
    agent_id: str
    host_id: str
    capacity: int
    max_concurrency: int
    control_plane_base_url: str


class AllInOneSettings(BaseModel):
    enabled_roles: tuple[AppRole, ...] = (
        AppRole.CONTROL_PLANE,
        AppRole.AGENT,
    )


class ControlPlaneAppSettings(BaseModel):
    role: AppRole = AppRole.CONTROL_PLANE
    shared: SharedSettings = Field(default_factory=SharedSettings)
    control_plane: ControlPlaneSettings = Field(default_factory=ControlPlaneSettings)


class AgentAppSettings(BaseModel):
    role: AppRole = AppRole.AGENT
    shared: SharedSettings = Field(default_factory=SharedSettings)
    agent: AgentSettings


class AllInOneAppSettings(BaseModel):
    role: AppRole = AppRole.ALL_IN_ONE
    shared: SharedSettings = Field(default_factory=SharedSettings)
    control_plane: ControlPlaneSettings = Field(default_factory=ControlPlaneSettings)
    agent: AgentSettings
    all_in_one: AllInOneSettings = Field(default_factory=AllInOneSettings)


RoleSettings = ControlPlaneAppSettings | AgentAppSettings | AllInOneAppSettings


class SettingsLoadError(Exception):
    def __init__(self, errors: list[dict[str, str]]) -> None:
        super().__init__("invalid application settings")
        self.errors = errors


_ENV_FIELD_MAP: dict[str, tuple[str, ...]] = {
    "OPPORTUNITY_CRAWLER_SHARED_ENVIRONMENT": ("shared", "environment"),
    "OPPORTUNITY_CRAWLER_SHARED_DATA_DIR": ("shared", "data_dir"),
    "OPPORTUNITY_CRAWLER_SHARED_LOG_DIR": ("shared", "log_dir"),
    "OPPORTUNITY_CRAWLER_SHARED_TMP_DIR": ("shared", "tmp_dir"),
    "OPPORTUNITY_CRAWLER_SHARED_DATABASE_PATH": ("shared", "database_path"),
    "OPPORTUNITY_CRAWLER_SHARED_EVIDENCE_DIR": ("shared", "evidence_dir"),
    "OPPORTUNITY_CRAWLER_SHARED_SCREENSHOTS_DIR": ("shared", "screenshots_dir"),
    "OPPORTUNITY_CRAWLER_SHARED_BROWSER_PROFILES_DIR": ("shared", "browser_profiles_dir"),
    "OPPORTUNITY_CRAWLER_CONTROL_PLANE_HOST": ("control_plane", "host"),
    "OPPORTUNITY_CRAWLER_CONTROL_PLANE_PORT": ("control_plane", "port"),
    "OPPORTUNITY_CRAWLER_CONTROL_PLANE_STATIC_URL_PREFIX": ("control_plane", "static_url_prefix"),
    "OPPORTUNITY_CRAWLER_CONTROL_PLANE_FRONTEND_DIST_DIR": ("control_plane", "frontend_dist_dir"),
    "OPPORTUNITY_CRAWLER_AGENT_AGENT_ID": ("agent", "agent_id"),
    "OPPORTUNITY_CRAWLER_AGENT_HOST_ID": ("agent", "host_id"),
    "OPPORTUNITY_CRAWLER_AGENT_CAPACITY": ("agent", "capacity"),
    "OPPORTUNITY_CRAWLER_AGENT_MAX_CONCURRENCY": ("agent", "max_concurrency"),
    "OPPORTUNITY_CRAWLER_AGENT_CONTROL_PLANE_BASE_URL": ("agent", "control_plane_base_url"),
    "OPPORTUNITY_CRAWLER_ALL_IN_ONE_ENABLED_ROLES": ("all_in_one", "enabled_roles"),
}


def load_settings(
    role: AppRole,
    config_path: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> RoleSettings:
    payload = _payload_for_role(role, _load_raw_settings(config_path))
    payload["role"] = role
    _apply_environment_overrides(payload, environ if environ is not None else os.environ)

    model_class = _model_class_for(role)
    try:
        return model_class.model_validate(payload)
    except ValidationError as exc:
        raise SettingsLoadError(_normalize_validation_errors(exc)) from exc


def _load_raw_settings(config_path: str | Path | None) -> dict[str, Any]:
    if config_path is None:
        return {}

    path = Path(config_path)
    if not path.exists():
        raise SettingsLoadError(
            [
                {
                    "field": "config_path",
                    "message": f"Config file not found: {path}",
                    "type": "not_found",
                }
            ]
        )

    with path.open("rb") as handle:
        return tomllib.load(handle)


def _payload_for_role(role: AppRole, raw_settings: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "shared": dict(raw_settings.get("shared", {})),
    }

    if role is AppRole.CONTROL_PLANE:
        payload["control_plane"] = dict(raw_settings.get("control_plane", {}))
    elif role is AppRole.AGENT:
        payload["agent"] = dict(raw_settings.get("agent", {}))
    elif role is AppRole.ALL_IN_ONE:
        payload["control_plane"] = dict(raw_settings.get("control_plane", {}))
        payload["agent"] = dict(raw_settings.get("agent", {}))
        payload["all_in_one"] = dict(raw_settings.get("all_in_one", {}))
    else:
        raise SettingsLoadError(
            [
                {
                    "field": "role",
                    "message": f"Unsupported role: {role}",
                    "type": "unsupported_role",
                }
            ]
        )

    return payload


def _apply_environment_overrides(payload: dict[str, Any], environ: Mapping[str, str]) -> None:
    for env_name, path in _ENV_FIELD_MAP.items():
        raw_value = environ.get(env_name)
        if raw_value is None:
            continue

        value: Any = raw_value
        try:
            if path[-1] in {"port", "capacity", "max_concurrency"}:
                value = int(raw_value)
            elif path[-1] == "enabled_roles":
                value = [part.strip() for part in raw_value.split(",") if part.strip()]
        except ValueError as exc:
            raise SettingsLoadError(
                [
                    {
                        "field": ".".join(path),
                        "message": f"Invalid integer value: {raw_value}",
                        "type": "invalid_value",
                    }
                ]
            ) from exc

        cursor = payload
        for key in path[:-1]:
            cursor = cursor.setdefault(key, {})
        cursor[path[-1]] = value


def _model_class_for(role: AppRole) -> type[ControlPlaneAppSettings] | type[AgentAppSettings] | type[AllInOneAppSettings]:
    if role is AppRole.CONTROL_PLANE:
        return ControlPlaneAppSettings
    if role is AppRole.AGENT:
        return AgentAppSettings
    if role is AppRole.ALL_IN_ONE:
        return AllInOneAppSettings
    raise SettingsLoadError(
        [
            {
                "field": "role",
                "message": f"Unsupported role: {role}",
                "type": "unsupported_role",
            }
        ]
    )


def _normalize_validation_errors(exc: ValidationError) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for issue in exc.errors():
        normalized.append(
            {
                "field": ".".join(str(part) for part in issue["loc"]),
                "message": str(issue["msg"]),
                "type": str(issue["type"]),
            }
        )
    return normalized
