from __future__ import annotations

import asyncio
import importlib.util
import json
import sqlite3
from pathlib import Path

from opportunity_crawler.agent.app import CollectionAgentApp
from opportunity_crawler.shared.contracts.agent_protocol import CollectionEventKind
from opportunity_crawler.control_plane.services.auth_service import AuthService


ROOT = Path(__file__).resolve().parents[2]


def test_dev_scripts_reference_opportunity_crawler_package() -> None:
    expected_scripts = [
        ROOT / "scripts" / "start_dev.sh",
        ROOT / "scripts" / "run_control_plane_dev.py",
        ROOT / "scripts" / "run_agent_dev.py",
        ROOT / "scripts" / "package_app.sh",
        ROOT / "scripts" / "start_backend.sh",
        ROOT / "scripts" / "start_frontend.sh",
        ROOT / "scripts" / "start_agent.sh",
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


def test_segmented_start_scripts_launch_independent_dev_processes() -> None:
    backend = (ROOT / "scripts" / "start_backend.sh").read_text(encoding="utf-8")
    frontend = (ROOT / "scripts" / "start_frontend.sh").read_text(encoding="utf-8")
    agent = (ROOT / "scripts" / "start_agent.sh").read_text(encoding="utf-8")

    assert "run_control_plane_dev.py" in backend
    assert "PYTHON_CMD" in backend
    assert "uv run python" in backend
    assert "OPPORTUNITY_CRAWLER_PYTHON" in backend
    assert backend.index("uv run python") < backend.index(".venv/bin/python")
    assert "OPPORTUNITY_CRAWLER_CONTROL_PLANE_PORT" in backend

    assert "VITE_API_PROXY_TARGET" in frontend
    assert 'npm --prefix "$ROOT_DIR/frontend" run dev' in frontend
    assert "OPPORTUNITY_CRAWLER_CONTROL_PLANE_PORT" in frontend

    assert "run_agent_dev.py" in agent
    assert "OPPORTUNITY_CRAWLER_AGENT_CONTROL_PLANE_BASE_URL" in agent
    assert "PYTHON_CMD" in agent
    assert "uv run python" in agent
    assert "OPPORTUNITY_CRAWLER_PYTHON" in agent
    assert agent.index("uv run python") < agent.index(".venv/bin/python")


def test_agent_dev_runner_derives_websocket_url_and_keeps_heartbeat_loop() -> None:
    module = _load_script_module(ROOT / "scripts" / "run_agent_dev.py")

    assert module.control_plane_ws_url("http://127.0.0.1:8000") == "ws://127.0.0.1:8000/api/agents/ws"
    assert module.control_plane_ws_url("https://control.example/base") == "wss://control.example/base/api/agents/ws"

    content = (ROOT / "scripts" / "run_agent_dev.py").read_text(encoding="utf-8")
    assert "asyncio.run" in content
    assert "send_heartbeat" in content
    assert "KeyboardInterrupt" in content


def test_agent_dev_runner_consumes_collection_command_and_sends_events() -> None:
    module = _load_script_module(ROOT / "scripts" / "run_agent_dev.py")
    asyncio.run(_assert_agent_dev_runner_consumes_collection_command_and_sends_events(module))


def test_agent_dev_runner_reconnects_after_service_restart(tmp_path: Path) -> None:
    module = _load_script_module(ROOT / "scripts" / "run_agent_dev.py")
    asyncio.run(_assert_agent_dev_runner_reconnects_after_service_restart(module, tmp_path))


def test_agent_dev_runner_wires_browser_runtime_into_source_session_manager(tmp_path: Path) -> None:
    module = _load_script_module(ROOT / "scripts" / "run_agent_dev.py")
    asyncio.run(_assert_agent_dev_runner_wires_browser_runtime_into_source_session_manager(module, tmp_path))


async def _assert_agent_dev_runner_consumes_collection_command_and_sends_events(module) -> None:
    websocket = FakeAgentWebSocket(
        [
            {
                "message_type": "collection_command",
                "command": "start_collection_run",
                "command_id": "cmd-1",
                "run_id": "run-1",
                "source_id": 1,
                "rule_version": 1,
                "adapter_mode": "manual_import",
                "login_mode": "not_required",
            }
        ]
    )
    app = CollectionAgentApp(
        runner=FakeRunner(),
        client=module.WebSocketEventClient(websocket),
    )

    await module.run_agent_message_loop(websocket, app, agent_id="agent-dev", heartbeat_interval=60, once=True)

    assert websocket.sent[0]["message_type"] == "collection_event"
    assert websocket.sent[0]["event_kind"] == "run_started"
    assert websocket.sent[0]["run_id"] == "run-1"
    assert websocket.sent[1]["message_type"] == "collection_event"
    assert websocket.sent[1]["event_kind"] == "run_succeeded"
    assert websocket.sent[1]["diagnostic_snapshot"] == {"from_runner": True}


async def _assert_agent_dev_runner_reconnects_after_service_restart(module, tmp_path: Path) -> None:
    config_path = tmp_path / "agent.toml"
    config_path.write_text(
        """
[shared]
browser_profiles_dir = "{browser_profiles_dir}"

[agent]
agent_id = "agent-dev"
host_id = "host-dev"
capacity = 1
max_concurrency = 1
control_plane_base_url = "http://127.0.0.1:8000"
""".format(browser_profiles_dir=tmp_path / "browser-profiles"),
        encoding="utf-8",
    )
    sockets = [
        FakeAgentWebSocket(
            [
                {"type": "registered", "agent_id": "agent-dev"},
            ],
            close_after_register=True,
        ),
        FakeAgentWebSocket(
            [
                {"type": "registered", "agent_id": "agent-dev"},
            ],
            close_after_register=True,
        ),
    ]
    connect_attempts = 0

    def connect_factory(*args, **kwargs):
        nonlocal connect_attempts
        _ = args, kwargs
        websocket = sockets[connect_attempts]
        connect_attempts += 1
        return FakeConnectContext(websocket)

    module.wait_for_control_plane = lambda base_url, timeout_seconds: None
    module.CamoufoxRuntime = lambda browser_profiles_dir: object()
    module.CollectionRunner = lambda browser_runtime, session_manager: FakeRunner()

    await module.run_agent(
        config_path,
        heartbeat_interval=60,
        startup_timeout=1,
        once=False,
        connect_factory=connect_factory,
        reconnect_delay=0,
        max_reconnects=1,
    )

    assert connect_attempts == 2
    assert sockets[0].sent[0]["type"] == "register"
    assert sockets[1].sent[0]["type"] == "register"


async def _assert_agent_dev_runner_wires_browser_runtime_into_source_session_manager(module, tmp_path: Path) -> None:
    captured = {}

    class FakeRuntime:
        pass

    class FakeSettings:
        class agent:
            agent_id = "agent-dev"
            host_id = "host-dev"
            capacity = 1

        class shared:
            browser_profiles_dir = tmp_path / "browser-profiles"

    def runtime_factory(browser_profiles_dir):
        runtime = FakeRuntime()
        captured["browser_profiles_dir"] = browser_profiles_dir
        captured["browser_runtime"] = runtime
        return runtime

    def collection_runner_factory(*, browser_runtime, session_manager):
        captured["runner_browser_runtime"] = browser_runtime
        captured["session_manager"] = session_manager
        return FakeRunner()

    module.CamoufoxRuntime = runtime_factory
    module.CollectionRunner = collection_runner_factory
    websocket = FakeAgentWebSocket(
        [
            {"type": "registered", "agent_id": "agent-dev"},
        ],
        close_after_register=True,
    )

    try:
        await module.run_agent_connection(
            connect_factory=lambda *args, **kwargs: FakeConnectContext(websocket),
            ws_url="ws://127.0.0.1:8000/api/agents/ws",
            settings=FakeSettings(),
            heartbeat_interval=60,
            once=False,
        )
    except FakeServiceRestart:
        pass

    assert captured["browser_profiles_dir"] == tmp_path / "browser-profiles"
    assert captured["runner_browser_runtime"] is captured["browser_runtime"]
    assert captured["session_manager"].runtime is captured["browser_runtime"]


def test_vite_dev_server_proxies_api_to_control_plane() -> None:
    content = (ROOT / "frontend" / "vite.config.ts").read_text(encoding="utf-8")

    assert "'/api'" in content
    assert "process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000'" in content
    assert "target: apiProxyTarget" in content
    assert "ws: true" in content


def test_python_project_declares_dev_startup_runtime_dependencies() -> None:
    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "camoufox" in content
    assert "fastapi" in content
    assert "uvicorn" in content
    assert "websockets" in content


def test_dev_runtime_artifacts_are_gitignored() -> None:
    content = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "/var/" in content
    assert ".venv/" in content
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


class FakeAgentWebSocket:
    def __init__(self, received: list[dict[str, object]], *, close_after_register: bool = False) -> None:
        self.received = [json.dumps(message) for message in received]
        self.close_after_register = close_after_register
        self.recv_count = 0
        self.sent: list[dict[str, object]] = []

    async def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))

    async def recv(self) -> str:
        self.recv_count += 1
        if self.close_after_register and self.recv_count > 1:
            raise FakeServiceRestart("received 1012 (service restart); then sent 1012 (service restart)")
        return self.received.pop(0)


class FakeConnectContext:
    def __init__(self, websocket: FakeAgentWebSocket) -> None:
        self.websocket = websocket

    async def __aenter__(self) -> FakeAgentWebSocket:
        return self.websocket

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None


class FakeServiceRestart(Exception):
    pass


class FakeRunner:
    async def start_collection_run(self, command):
        return {
            "event_kind": CollectionEventKind.RUN_SUCCEEDED,
            "command_id": command.command_id,
            "run_id": command.run_id,
            "source_id": command.source_id,
            "adapter_mode": command.adapter_mode,
            "page_count": 1,
            "item_count": 0,
            "rows": [],
            "diagnostic_snapshot": {"from_runner": True},
        }
