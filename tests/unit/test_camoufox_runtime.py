from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.agent.browser.camoufox_runtime import CamoufoxRuntime
from opportunity_crawler.agent.runtime.session_manager import SourceSessionOpenRequest


def test_camoufox_runtime_uses_source_account_profile_directory(tmp_path: Path) -> None:
    created_profiles: list[Path] = []

    def browser_factory(profile_path: Path) -> object:
        created_profiles.append(profile_path)
        return {"profile_path": str(profile_path)}

    runtime = CamoufoxRuntime(browser_profiles_dir=tmp_path, browser_factory=browser_factory)

    session = runtime.open_session(
        SourceSessionOpenRequest(source_account_id=7, source_id=3, command_id="cmd-1")
    )

    assert session.session_id == "source-account-7"
    assert session.profile_path == tmp_path / "source-account-7"
    assert created_profiles == [tmp_path / "source-account-7"]
    runtime.ensure_session_alive(session.session_id)
    runtime.close_session(session.session_id)

