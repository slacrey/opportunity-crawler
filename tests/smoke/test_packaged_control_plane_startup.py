from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.control_plane.app import create_app
from opportunity_crawler.shared.config import AppRole, load_settings
from opportunity_crawler.shared.db.base import apply_migrations, connect_sqlite


def test_packaged_control_plane_contract_starts_with_custom_data_paths(tmp_path: Path) -> None:
    config_path = tmp_path / "control-plane.toml"
    database_path = tmp_path / "data" / "opportunity.db"
    config_path.write_text(
        f"""
[shared]
environment = "packaged"
data_dir = "{tmp_path / 'data'}"
log_dir = "{tmp_path / 'logs'}"
tmp_dir = "{tmp_path / 'tmp'}"
database_path = "{database_path}"
evidence_dir = "{tmp_path / 'data' / 'evidence'}"
screenshots_dir = "{tmp_path / 'data' / 'screenshots'}"
browser_profiles_dir = "{tmp_path / 'data' / 'browser-profiles'}"

[control_plane]
host = "127.0.0.1"
port = 0
static_url_prefix = "/static"
frontend_dist_dir = "./frontend/dist"
""".strip(),
        encoding="utf-8",
    )
    settings = load_settings(AppRole.CONTROL_PLANE, config_path=config_path)
    connection = connect_sqlite(settings.shared.database_path)
    apply_migrations(connection)
    connection.close()

    client = TestClient(create_app(database_path=settings.shared.database_path))
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["database"]["ok"] is True
    assert settings.shared.evidence_dir == tmp_path / "data" / "evidence"

