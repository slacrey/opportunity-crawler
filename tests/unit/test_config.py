from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.bootstrap.agent import build_runtime as build_agent_runtime
from opportunity_crawler.bootstrap.all_in_one import build_runtime as build_all_in_one_runtime
from opportunity_crawler.bootstrap.control_plane import build_runtime
from opportunity_crawler.shared.config import AppRole, SettingsLoadError, load_settings


def test_load_settings_merges_toml_with_environment_overrides(tmp_path: Path) -> None:
    config_path = tmp_path / "control-plane.toml"
    config_path.write_text(
        """
[shared]
environment = "staging"
data_dir = "/srv/opportunity/data"
log_dir = "/srv/opportunity/logs"
tmp_dir = "/srv/opportunity/tmp"
database_path = "/srv/opportunity/data/opportunity.db"
evidence_dir = "/srv/opportunity/evidence"
screenshots_dir = "/srv/opportunity/screenshots"
browser_profiles_dir = "/srv/opportunity/browser-profiles"

[control_plane]
host = "127.0.0.1"
port = 8100
static_url_prefix = "/static"
""".strip(),
        encoding="utf-8",
    )

    settings = load_settings(
        role=AppRole.CONTROL_PLANE,
        config_path=config_path,
        environ={"OPPORTUNITY_CRAWLER_CONTROL_PLANE_PORT": "9100"},
    )

    assert settings.role is AppRole.CONTROL_PLANE
    assert settings.shared.environment == "staging"
    assert settings.shared.database_path == Path("/srv/opportunity/data/opportunity.db")
    assert settings.shared.evidence_dir == Path("/srv/opportunity/evidence")
    assert settings.shared.screenshots_dir == Path("/srv/opportunity/screenshots")
    assert settings.shared.browser_profiles_dir == Path("/srv/opportunity/browser-profiles")
    assert settings.control_plane.port == 9100


def test_load_settings_returns_stable_missing_agent_error_shape(tmp_path: Path) -> None:
    config_path = tmp_path / "agent.toml"
    config_path.write_text(
        """
[shared]
environment = "development"
""".strip(),
        encoding="utf-8",
    )

    try:
        load_settings(role=AppRole.AGENT, config_path=config_path, environ={})
    except SettingsLoadError as exc:
        assert exc.errors == [
            {"field": "agent.agent_id", "message": "Field required", "type": "missing"},
            {"field": "agent.host_id", "message": "Field required", "type": "missing"},
            {"field": "agent.capacity", "message": "Field required", "type": "missing"},
            {"field": "agent.max_concurrency", "message": "Field required", "type": "missing"},
            {
                "field": "agent.control_plane_base_url",
                "message": "Field required",
                "type": "missing",
            },
        ]
    else:
        raise AssertionError("expected SettingsLoadError")


def test_invalid_environment_override_returns_structured_error() -> None:
    try:
        load_settings(
            role=AppRole.CONTROL_PLANE,
            environ={"OPPORTUNITY_CRAWLER_CONTROL_PLANE_PORT": "not-a-number"},
        )
    except SettingsLoadError as exc:
        assert exc.errors == [
            {
                "field": "control_plane.port",
                "message": "Invalid integer value: not-a-number",
                "type": "invalid_value",
            }
        ]
    else:
        raise AssertionError("expected SettingsLoadError")


def test_control_plane_bootstrap_uses_shared_settings_loader(tmp_path: Path) -> None:
    config_path = tmp_path / "control-plane.toml"
    config_path.write_text(
        """
[control_plane]
host = "0.0.0.0"
port = 8200
static_url_prefix = "/assets"
""".strip(),
        encoding="utf-8",
    )

    runtime = build_runtime(config_path=config_path, environ={})

    assert runtime.role is AppRole.CONTROL_PLANE
    assert runtime.settings.control_plane.host == "0.0.0.0"
    assert runtime.settings.control_plane.static_url_prefix == "/assets"


def test_agent_bootstrap_uses_shared_settings_loader(tmp_path: Path) -> None:
    config_path = tmp_path / "agent.toml"
    config_path.write_text(
        """
[agent]
agent_id = "agent-01"
host_id = "host-01"
capacity = 4
max_concurrency = 2
control_plane_base_url = "http://127.0.0.1:8200"
""".strip(),
        encoding="utf-8",
    )

    runtime = build_agent_runtime(config_path=config_path, environ={})

    assert runtime.role is AppRole.AGENT
    assert runtime.settings.agent.agent_id == "agent-01"
    assert runtime.settings.agent.host_id == "host-01"
    assert runtime.settings.agent.capacity == 4
    assert runtime.settings.agent.max_concurrency == 2
    assert runtime.settings.agent.control_plane_base_url == "http://127.0.0.1:8200"


def test_all_in_one_bootstrap_loads_combined_sections(tmp_path: Path) -> None:
    config_path = tmp_path / "all-in-one.toml"
    config_path.write_text(
        """
[control_plane]
host = "127.0.0.1"
port = 8300
static_url_prefix = "/static"

[agent]
agent_id = "agent-02"
host_id = "host-02"
capacity = 1
max_concurrency = 1
control_plane_base_url = "http://127.0.0.1:8300"

[all_in_one]
enabled_roles = ["control_plane", "agent"]
""".strip(),
        encoding="utf-8",
    )

    runtime = build_all_in_one_runtime(
        config_path=config_path,
        environ={"OPPORTUNITY_CRAWLER_ALL_IN_ONE_ENABLED_ROLES": "control_plane,agent"},
    )

    assert runtime.role is AppRole.ALL_IN_ONE
    assert runtime.settings.control_plane.port == 8300
    assert runtime.settings.agent.agent_id == "agent-02"
    assert runtime.settings.agent.host_id == "host-02"
    assert runtime.settings.all_in_one.enabled_roles == (
        AppRole.CONTROL_PLANE,
        AppRole.AGENT,
    )
