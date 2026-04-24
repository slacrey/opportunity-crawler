from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.shared.config import AppRole, load_settings


def test_dev_extra_declares_pyinstaller() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "pyinstaller>=6.6,<7.0" in pyproject["project"]["optional-dependencies"]["dev"]


def test_default_config_templates_load_for_packaged_roles() -> None:
    defaults = ROOT / "packaging" / "defaults"

    control_plane = load_settings(AppRole.CONTROL_PLANE, config_path=defaults / "control_plane.toml")
    agent = load_settings(AppRole.AGENT, config_path=defaults / "agent.toml")
    all_in_one = load_settings(AppRole.ALL_IN_ONE, config_path=defaults / "all_in_one.toml")

    assert control_plane.control_plane.frontend_dist_dir == Path("./frontend/dist")
    assert agent.agent.control_plane_base_url.startswith("http://127.0.0.1")
    assert all_in_one.all_in_one.enabled_roles == (AppRole.CONTROL_PLANE, AppRole.AGENT)


def test_pyinstaller_common_declares_required_resource_manifests() -> None:
    common = _load_packaging_common()

    resources = {resource.name: resource for resource in common.resource_manifests()}

    assert resources["default_config_templates"].target == "packaging/defaults"
    assert resources["database_migrations"].target == "migrations/versions"
    assert resources["frontend_static_assets"].target == "frontend/dist"
    assert "opportunity_crawler.shared.domain.rules" in common.pyinstaller_hiddenimports()


def test_pyinstaller_specs_exist_and_share_packaging_contract() -> None:
    spec_dir = ROOT / "packaging" / "pyinstaller"

    for role, artifact in (
        ("control_plane", "opportunity-crawler-control-plane"),
        ("agent", "opportunity-crawler-agent"),
        ("all_in_one", "opportunity-crawler-all-in-one"),
    ):
        content = (spec_dir / f"{role}.spec").read_text(encoding="utf-8")
        assert "load_common_module" in content
        assert "common.pyinstaller_datas()" in content
        assert f'"{role}_main.py"' in content
        assert f'name="{artifact}"' in content


def _load_packaging_common():
    common_path = ROOT / "packaging" / "pyinstaller" / "common.py"
    spec = importlib.util.spec_from_file_location("opportunity_crawler_packaging_common", common_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
