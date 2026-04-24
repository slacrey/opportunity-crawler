from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol


@dataclass(frozen=True, slots=True)
class SourceSessionOpenRequest:
    source_account_id: int
    source_id: int
    command_id: str


@dataclass(frozen=True, slots=True)
class SourceSessionConflictError(Exception):
    source_account_id: int

    def __str__(self) -> str:
        return f"source account {self.source_account_id} already has an active session"


class BrowserRuntime(Protocol):
    def open_session(self, request: SourceSessionOpenRequest) -> Any: ...

    def ensure_session_alive(self, session_id: str) -> None: ...

    def close_session(self, session_id: str) -> None: ...

    def clear_source_account_state(self, source_account_id: int) -> None: ...


class SourceSessionManager:
    def __init__(self, runtime: BrowserRuntime) -> None:
        self.runtime = runtime
        self._sessions: dict[int, Any] = {}

    def open_session(self, request: SourceSessionOpenRequest) -> Any:
        if request.source_account_id in self._sessions:
            raise SourceSessionConflictError(source_account_id=request.source_account_id)
        session = self.runtime.open_session(request)
        self._sessions[request.source_account_id] = session
        return session

    def keep_session(self, source_account_id: int) -> Any:
        session = self._sessions[source_account_id]
        self.runtime.ensure_session_alive(_session_id(session))
        return session

    def release_session(self, source_account_id: int, *, clear_browser_state: bool = False) -> Any | None:
        session = self._sessions.pop(source_account_id, None)
        if session is not None:
            self.runtime.close_session(_session_id(session))
        if clear_browser_state:
            self.runtime.clear_source_account_state(source_account_id)
        return session

    def get_session(self, source_account_id: int) -> Any | None:
        return self._sessions.get(source_account_id)

    def active_source_account_ids(self) -> tuple[int, ...]:
        return tuple(self._sessions)


def _session_id(session: Any) -> str:
    if isinstance(session, Mapping):
        value = session.get("session_id")
        if isinstance(value, str):
            return value
    value = getattr(session, "session_id", None)
    if isinstance(value, str):
        return value
    raise TypeError("session object does not expose a string session_id")

