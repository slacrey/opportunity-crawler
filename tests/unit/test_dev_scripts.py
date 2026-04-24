from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

from opportunity_crawler.control_plane.services.auth_service import AuthService


ROOT = Path(__file__).resolve().parents[2]


def test_dev_scripts_reference_opportunity_crawler_package() -> None:
    expected_scripts = [
        ROOT / "scripts" / "start_dev.sh",
        ROOT / "scripts" / "run_control_plane_dev.py",
        ROOT / "scripts" / "run_agent_dev.py",
        ROOT / "scripts" / "package_app.sh",
    ]

    for script_path in expected_scripts:
        content = script_path.read_text(encoding="utf-8")
        assert "opportunity_crawler" in content
        assert "crawler_monitor" not in content
        assert "alipay" not in content.lower()


def test_frontend_vite_env_typings_only_expose_non_secret_runtime_urls() -> None:
    env_typings = ROOT / "frontend" / "src" / "vite-env.d.ts"

    content = env_typings.read_text(encoding="utf-8")

    assert "VITE_API_BASE_URL" in content
    assert "VITE_EVENT_STREAM_URL" in content
    assert "SECRET" not in content
    assert "TOKEN" not in content
    assert "PASSWORD" not in content


def test_control_plane_dev_runner_prepares_database_and_seed_users(tmp_path: Path) -> None:
    module = _load_script_module(ROOT / "scripts" / "run_control_plane_dev.py")
    database_path = tmp_path / "data" / "opportunity.db"

    module.prepare_database(database_path)

    with sqlite3.connect(database_path) as connection:
        migration_count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
        admin = connection.execute(
            """
            SELECT u.password_hash, r.name
            FROM users u
            JOIN user_roles ur ON ur.user_id = u.id
            JOIN roles r ON r.id = ur.role_id
            WHERE u.username = 'admin'
            """,
        ).fetchone()
        business_user = connection.execute(
            """
            SELECT u.password_hash, r.name
            FROM users u
            JOIN user_roles ur ON ur.user_id = u.id
            JOIN roles r ON r.id = ur.role_id
            WHERE u.username = 'biz'
            """,
        ).fetchone()

    assert migration_count > 0
    assert admin == (AuthService.hash_password("admin-pass"), "administrator")
    assert business_user == (AuthService.hash_password("biz-pass"), "business_manager")


def test_start_dev_script_runs_backend_health_check_then_frontend() -> None:
    content = (ROOT / "scripts" / "start_dev.sh").read_text(encoding="utf-8")

    assert "run_control_plane_dev.py" in content
    assert "/api/health" in content
    assert "npm --prefix \"$ROOT_DIR/frontend\" run dev" in content
    assert "trap cleanup EXIT INT TERM" in content
    assert "OPPORTUNITY_CRAWLER_CONTROL_PLANE_PORT" in content


def test_vite_dev_server_proxies_api_to_control_plane() -> None:
    content = (ROOT / "frontend" / "vite.config.ts").read_text(encoding="utf-8")

    assert "'/api'" in content
    assert "process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000'" in content
    assert "target: apiProxyTarget" in content
    assert "ws: true" in content


def test_python_project_declares_dev_startup_runtime_dependencies() -> None:
    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "fastapi" in content
    assert "uvicorn" in content


def test_dev_runtime_artifacts_are_gitignored() -> None:
    content = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "/var/" in content
    assert "__pycache__/" in content
    assert "*.pyc" in content


def test_package_script_builds_frontend_pyinstaller_sidecars_and_optional_desktop_bundle() -> None:
    content = (ROOT / "scripts" / "package_app.sh").read_text(encoding="utf-8")

    assert 'npm --prefix "$ROOT_DIR/frontend" run build' in content
    assert "python3" in content
    assert "-m PyInstaller" in content
    assert "PYINSTALLER_CONFIG_DIR" in content
    assert "packaging/pyinstaller/control_plane.spec" in content
    assert "packaging/pyinstaller/agent.spec" in content
    assert "packaging/pyinstaller/all_in_one.spec" in content
    assert "detect_tauri_target_triple" in content
    assert "src-tauri/binaries" in content
    assert "--desktop" in content
    assert "cargo tauri build" in content


def test_root_package_json_exposes_packaging_commands() -> None:
    content = (ROOT / "package.json").read_text(encoding="utf-8")

    assert '"package:app": "bash scripts/package_app.sh"' in content
    assert '"package:desktop": "bash scripts/package_app.sh --desktop"' in content


def _load_script_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
