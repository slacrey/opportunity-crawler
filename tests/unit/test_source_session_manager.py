from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.agent.runtime.session_manager import (
    SourceSessionConflictError,
    SourceSessionManager,
    SourceSessionOpenRequest,
)


class FakeRuntime:
    def __init__(self) -> None:
        self.closed: list[str] = []

    def open_session(self, request: SourceSessionOpenRequest) -> dict[str, str]:
        return {"session_id": f"source-account-{request.source_account_id}"}

    def ensure_session_alive(self, session_id: str) -> None:
        return None

    def close_session(self, session_id: str) -> None:
        self.closed.append(session_id)

    def clear_source_account_state(self, source_account_id: int) -> None:
        return None


def test_session_manager_rejects_duplicate_source_account_session() -> None:
    manager = SourceSessionManager(FakeRuntime())
    request = SourceSessionOpenRequest(source_account_id=1, source_id=10, command_id="cmd-1")

    manager.open_session(request)

    try:
        manager.open_session(request)
    except SourceSessionConflictError as exc:
        assert exc.source_account_id == 1
    else:
        raise AssertionError("expected SourceSessionConflictError")


def test_session_manager_releases_only_requested_session() -> None:
    runtime = FakeRuntime()
    manager = SourceSessionManager(runtime)

    manager.open_session(SourceSessionOpenRequest(source_account_id=1, source_id=10, command_id="cmd-1"))
    manager.open_session(SourceSessionOpenRequest(source_account_id=2, source_id=20, command_id="cmd-2"))
    manager.release_session(1)

    assert runtime.closed == ["source-account-1"]
    assert manager.get_session(2) is not None

