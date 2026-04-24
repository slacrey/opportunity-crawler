from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.control_plane.services.runtime_registry import RuntimeRegistry
from opportunity_crawler.shared.db.base import apply_migrations, connect_sqlite


def test_runtime_registry_registers_and_heartbeats_agent(tmp_path: Path) -> None:
    database_path = tmp_path / "opportunity.db"
    connection = connect_sqlite(database_path)
    apply_migrations(connection)
    connection.close()
    registry = RuntimeRegistry(database_path)

    presence = registry.register(
        {
            "agent_id": "agent-1",
            "host_id": "host-1",
            "hostname": "localhost",
            "platform": "darwin",
            "app_version": "0.1.0",
            "capacity": 2,
        }
    )
    heartbeat = registry.heartbeat("agent-1")

    assert presence["online"] is True
    assert heartbeat["agent_id"] == "agent-1"


def test_runtime_registry_rejects_commands_for_offline_agent(tmp_path: Path) -> None:
    database_path = tmp_path / "opportunity.db"
    connection = connect_sqlite(database_path)
    apply_migrations(connection)
    connection.close()
    registry = RuntimeRegistry(database_path)

    try:
        registry.dispatch_command("missing-agent", {"type": "start_collection_run"})
    except KeyError as exc:
        assert "missing-agent" in str(exc)
    else:
        raise AssertionError("expected KeyError")
