from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.agent.browser.camoufox_runtime import CamoufoxRuntime
import opportunity_crawler.agent.browser.camoufox_runtime as camoufox_runtime
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


def test_camoufox_runtime_fetches_html_through_configured_fetcher(tmp_path: Path) -> None:
    requested_urls: list[str] = []

    def html_fetcher(url: str) -> str:
        requested_urls.append(url)
        return "<html><body>ok</body></html>"

    runtime = CamoufoxRuntime(browser_profiles_dir=tmp_path, html_fetcher=html_fetcher)

    html = runtime.fetch_html("https://example.test")

    assert html == "<html><body>ok</body></html>"
    assert requested_urls == ["https://example.test"]


def test_camoufox_runtime_fetches_html_by_opening_browser_page(tmp_path: Path) -> None:
    browser = FakeBrowser()

    runtime = CamoufoxRuntime(browser_profiles_dir=tmp_path, browser_factory=lambda profile_path: browser)

    html = runtime.fetch_html("https://example.test/search")

    assert html == "<html><body>browser rendered</body></html>"
    assert browser.profile_path == tmp_path / "public-fetch"
    assert browser.pages[0].visited_urls == ["https://example.test/search"]
    assert browser.pages[0].closed is True


def test_camoufox_runtime_falls_back_to_urllib_when_browser_is_unavailable(tmp_path: Path, monkeypatch) -> None:
    fetched_urls: list[str] = []

    def browser_factory(profile_path: Path) -> object:
        _ = profile_path
        raise RuntimeError("camoufox unavailable")

    def urllib_fetcher(url: str) -> str:
        fetched_urls.append(url)
        return "<html><body>urllib fallback</body></html>"

    monkeypatch.setattr(camoufox_runtime, "_fetch_html_with_urllib", urllib_fetcher)
    runtime = CamoufoxRuntime(browser_profiles_dir=tmp_path, browser_factory=browser_factory)

    html = runtime.fetch_html("https://example.test/search")

    assert html == "<html><body>urllib fallback</body></html>"
    assert fetched_urls == ["https://example.test/search"]


def test_camoufox_runtime_opens_initial_url_for_source_session(tmp_path: Path) -> None:
    browser = FakeBrowser()
    runtime = CamoufoxRuntime(browser_profiles_dir=tmp_path, browser_factory=lambda profile_path: browser)

    session = runtime.open_session(
        SourceSessionOpenRequest(
            source_account_id=7,
            source_id=3,
            command_id="cmd-1",
            initial_url="https://example.test/login",
        )
    )

    assert session.session_id == "source-account-7"
    assert browser.pages[0].visited_urls == ["https://example.test/login"]
    assert browser.pages[0].closed is False


def test_camoufox_runtime_submits_search_with_browser_controls(tmp_path: Path) -> None:
    browser = FakeBrowser()
    runtime = CamoufoxRuntime(browser_profiles_dir=tmp_path, browser_factory=lambda profile_path: browser)

    html = runtime.submit_search(
        "https://example.test/search",
        "昆山 AI",
        selectors={
            "search_input_selector": "#keyword",
            "search_button_selector": "#submit",
        },
        rule_payload={},
    )

    assert html == "<html><body>browser rendered</body></html>"
    assert browser.pages[0].visited_urls == ["https://example.test/search"]
    assert browser.pages[0].filled == [("#keyword", "昆山 AI")]
    assert browser.pages[0].clicked == ["#submit"]


class FakeBrowser:
    def __init__(self) -> None:
        self.profile_path: Path | None = None
        self.pages: list[FakePage] = []

    def new_page(self) -> "FakePage":
        page = FakePage()
        self.pages.append(page)
        return page


class FakePage:
    def __init__(self) -> None:
        self.visited_urls: list[str] = []
        self.filled: list[tuple[str, str]] = []
        self.clicked: list[str] = []
        self.closed = False

    def goto(self, url: str, **kwargs: object) -> None:
        _ = kwargs
        self.visited_urls.append(url)

    def fill(self, selector: str, value: str) -> None:
        self.filled.append((selector, value))

    def click(self, selector: str) -> None:
        self.clicked.append(selector)

    def content(self) -> str:
        return "<html><body>browser rendered</body></html>"

    def close(self) -> None:
        self.closed = True
