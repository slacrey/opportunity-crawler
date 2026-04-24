from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opportunity_crawler.shared.db.base import connect_sqlite


class RuntimeRegistry:
    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self._online_agents: dict[str, dict[str, Any]] = {}
        self._commands: dict[str, list[dict[str, Any]]] = {}

    def register(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = _utc_now()
        agent_id = str(payload["agent_id"])
        host_id = str(payload["host_id"])
        presence = {
            "agent_id": agent_id,
            "host_id": host_id,
            "hostname": payload.get("hostname") or host_id,
            "platform": payload.get("platform"),
            "app_version": payload.get("app_version"),
            "capacity": int(payload.get("capacity") or 1),
            "active_sessions": 0,
            "online": True,
            "last_heartbeat_at": now,
        }
        self._online_agents[agent_id] = presence
        with connect_sqlite(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO agent_hosts (host_id, hostname, platform, app_version, last_seen_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(host_id) DO UPDATE SET
                    hostname = excluded.hostname,
                    platform = excluded.platform,
                    app_version = excluded.app_version,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    host_id,
                    presence["hostname"],
                    presence["platform"],
                    presence["app_version"],
                    now,
                ),
            )
            connection.execute(
                """
                INSERT INTO agent_instances (
                    agent_id, host_id, status, capacity, active_sessions, last_heartbeat_at
                )
                VALUES (?, ?, 'online', ?, 0, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    host_id = excluded.host_id,
                    status = 'online',
                    capacity = excluded.capacity,
                    last_heartbeat_at = excluded.last_heartbeat_at
                """,
                (agent_id, host_id, presence["capacity"], now),
            )
            connection.commit()
        return presence

    def heartbeat(self, agent_id: str) -> dict[str, Any]:
        if agent_id not in self._online_agents:
            raise KeyError(f"unknown agent: {agent_id}")
        now = _utc_now()
        self._online_agents[agent_id]["last_heartbeat_at"] = now
        with connect_sqlite(self.database_path) as connection:
            connection.execute(
                """
                UPDATE agent_instances
                SET status = 'online', last_heartbeat_at = ?
                WHERE agent_id = ?
                """,
                (now, agent_id),
            )
            connection.commit()
        return self._online_agents[agent_id]

    def dispatch_command(self, agent_id: str, command: dict[str, Any]) -> dict[str, Any]:
        if agent_id not in self._online_agents:
            raise KeyError(f"unknown agent: {agent_id}")
        self._commands.setdefault(agent_id, []).append(command)
        return {"agent_id": agent_id, "queued": True, "command": command}

    def online_count(self) -> int:
        return len(self._online_agents)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

