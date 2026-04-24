from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from opportunity_crawler.agent.runtime.session_manager import SourceSessionOpenRequest


@dataclass(frozen=True)
class BrowserSession:
    session_id: str
    source_account_id: int
    source_id: int
    profile_path: Path
    browser: Any
    alive: bool = True


class CamoufoxRuntime:
    def __init__(
        self,
        *,
        browser_profiles_dir: str | Path,
        browser_factory: Callable[[Path], Any] | None = None,
    ) -> None:
        self.browser_profiles_dir = Path(browser_profiles_dir)
        self.browser_factory = browser_factory or (lambda profile_path: {"profile_path": str(profile_path)})
        self._sessions: dict[str, BrowserSession] = {}

    def open_session(self, request: SourceSessionOpenRequest) -> BrowserSession:
        session_id = f"source-account-{request.source_account_id}"
        profile_path = self.browser_profiles_dir / session_id
        profile_path.mkdir(parents=True, exist_ok=True)
        browser = self.browser_factory(profile_path)
        session = BrowserSession(
            session_id=session_id,
            source_account_id=request.source_account_id,
            source_id=request.source_id,
            profile_path=profile_path,
            browser=browser,
        )
        self._sessions[session_id] = session
        return session

    def ensure_session_alive(self, session_id: str) -> None:
        if session_id not in self._sessions:
            raise RuntimeError(f"browser session is not open: {session_id}")

    def close_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def clear_source_account_state(self, source_account_id: int) -> None:
        _ = source_account_id

