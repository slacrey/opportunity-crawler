from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_dev_scripts_reference_opportunity_crawler_package() -> None:
    expected_scripts = [
        ROOT / "scripts" / "start_dev.sh",
        ROOT / "scripts" / "run_control_plane_dev.py",
        ROOT / "scripts" / "run_agent_dev.py",
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
