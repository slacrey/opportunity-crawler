from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import platform
import sys
import time
from typing import Any
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.agent.app import CollectionAgentApp
from opportunity_crawler.agent.browser.camoufox_runtime import CamoufoxRuntime
from opportunity_crawler.agent.runtime.collection_runner import CollectionRunner
from opportunity_crawler.bootstrap.agent import build_runtime
from opportunity_crawler.shared.contracts.agent_protocol import CollectionEventMessage


DEFAULT_CONFIG = ROOT / "packaging" / "defaults" / "agent.toml"


def control_plane_ws_url(base_url: str) -> str:
    parsed = urllib.parse.urlsplit(base_url.rstrip("/"))
    scheme = "wss" if parsed.scheme == "https" else "ws"
    base_path = parsed.path.rstrip("/")
    path = f"{base_path}/api/agents/ws" if base_path else "/api/agents/ws"
    return urllib.parse.urlunsplit((scheme, parsed.netloc, path, "", ""))


def wait_for_control_plane(base_url: str, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    health_url = f"{base_url.rstrip('/')}/api/health"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.25)
    raise TimeoutError(f"Timed out waiting for {health_url}")


async def send_heartbeat(websocket: Any, agent_id: str) -> None:
    await websocket.send(json.dumps({"type": "heartbeat", "agent_id": agent_id}))


class WebSocketEventClient:
    def __init__(self, websocket: Any) -> None:
        self.websocket = websocket

    async def send_collection_event(self, **payload: Any) -> None:
        event = CollectionEventMessage(message_type="collection_event", **payload)
        await self.websocket.send(json.dumps(event.model_dump(mode="json")))


async def run_agent_message_loop(
    websocket: Any,
    app: CollectionAgentApp,
    *,
    agent_id: str,
    heartbeat_interval: float,
    once: bool = False,
) -> None:
    while True:
        try:
            raw_payload = await asyncio.wait_for(websocket.recv(), timeout=heartbeat_interval)
        except asyncio.TimeoutError:
            await send_heartbeat(websocket, agent_id)
            continue

        payload = json.loads(raw_payload)
        message_type = payload.get("message_type") or payload.get("type")
        if message_type == "collection_command":
            await app.handle_command(payload)
            if once:
                return
        elif once:
            return


async def run_agent(config_path: Path, heartbeat_interval: float, startup_timeout: float, once: bool) -> None:
    runtime = build_runtime(config_path=config_path)
    settings = runtime.settings
    base_url = settings.agent.control_plane_base_url
    wait_for_control_plane(base_url, startup_timeout)
    ws_url = control_plane_ws_url(base_url)

    try:
        from websockets.asyncio.client import connect
    except ModuleNotFoundError as exc:
        raise RuntimeError("websockets package is required to start the development Agent") from exc

    async with connect(ws_url, ping_interval=None, proxy=None) as websocket:
        register = {
            "type": "register",
            "agent_id": settings.agent.agent_id,
            "host_id": settings.agent.host_id,
            "hostname": platform.node() or "localhost",
            "platform": platform.system().lower(),
            "app_version": "0.1.0",
            "capacity": settings.agent.capacity,
        }
        await websocket.send(json.dumps(register))
        registered = json.loads(await websocket.recv())
        if registered.get("type") != "registered":
            raise RuntimeError(f"Agent registration failed: {registered}")
        print(f"Agent registered: {settings.agent.agent_id} -> {ws_url}", flush=True)

        if once:
            return

        event_client = WebSocketEventClient(websocket)
        browser_runtime = CamoufoxRuntime(browser_profiles_dir=settings.shared.browser_profiles_dir)
        app = CollectionAgentApp(
            runner=CollectionRunner(browser_runtime=browser_runtime),
            client=event_client,
        )

        await run_agent_message_loop(
            websocket,
            app,
            agent_id=settings.agent.agent_id,
            heartbeat_interval=heartbeat_interval,
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Opportunity Crawler Agent for local development.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--heartbeat-interval", type=float, default=20.0)
    parser.add_argument("--startup-timeout", type=float, default=30.0)
    parser.add_argument("--once", action="store_true", help="Register once and exit; useful for smoke checks.")
    args = parser.parse_args(argv)

    try:
        asyncio.run(run_agent(args.config, args.heartbeat_interval, args.startup_timeout, args.once))
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
