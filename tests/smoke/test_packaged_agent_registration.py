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


def test_packaged_agent_contract_registers_against_control_plane(tmp_path: Path) -> None:
    database_path = tmp_path / "control-plane.db"
    connection = connect_sqlite(database_path)
    apply_migrations(connection)
    connection.close()
    settings = load_settings(AppRole.AGENT, config_path=ROOT / "packaging" / "defaults" / "agent.toml")

    client = TestClient(create_app(database_path=database_path))
    with client.websocket_connect("/api/agents/ws") as websocket:
        websocket.send_json(
            {
                "type": "register",
                "agent_id": settings.agent.agent_id,
                "host_id": settings.agent.host_id,
                "hostname": "packaged-smoke",
                "platform": "darwin",
                "app_version": "0.1.0",
                "capacity": settings.agent.capacity,
            }
        )
        response = websocket.receive_json()

    assert response == {"type": "registered", "agent_id": settings.agent.agent_id}

