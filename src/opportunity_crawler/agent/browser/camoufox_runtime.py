from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import shutil
from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import urllib.request

from opportunity_crawler.agent.runtime.session_manager import SourceSessionOpenRequest


logger = logging.getLogger(__name__)
DEFAULT_CAMOUFOX_LOCALE = "zh-CN"
DEFAULT_CAMOUFOX_WINDOW = (1440, 900)
DEFAULT_CAMOUFOX_FONTS = [
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "PingFang SC",
    "Hiragino Sans GB",
    "Microsoft YaHei",
    "SimSun",
    "WenQuanYi Zen Hei",
    "Arial Unicode MS",
]


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
        html_fetcher: Callable[[str], str] | None = None,
    ) -> None:
        self.browser_profiles_dir = Path(browser_profiles_dir)
        self.browser_factory = browser_factory or _launch_camoufox_browser
        self.html_fetcher = html_fetcher
        self._fetch_browser: Any | None = None
        self._sessions: dict[str, BrowserSession] = {}

    def open_session(self, request: SourceSessionOpenRequest) -> BrowserSession:
        session_id = f"source-account-{request.source_account_id}"
        profile_path = self.browser_profiles_dir / session_id
        profile_path.mkdir(parents=True, exist_ok=True)
        browser = self.browser_factory(profile_path)
        if hasattr(browser, "profile_path"):
            setattr(browser, "profile_path", profile_path)
        if request.initial_url is not None:
            _open_initial_url(browser, request.initial_url)
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
        session = self._sessions.get(session_id)
        if session is None:
            raise RuntimeError(f"browser session is not open: {session_id}")
        _ensure_browser_alive(session.browser)

    def close_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return
        close = getattr(session.browser, "close", None)
        if callable(close):
            close()

    def clear_source_account_state(self, source_account_id: int) -> None:
        shutil.rmtree(self.browser_profiles_dir / f"source-account-{source_account_id}", ignore_errors=True)

    def fetch_html(self, url: str) -> str:
        if self.html_fetcher is not None:
            return self.html_fetcher(url)
        html = self._fetch_html_with_browser(url)
        if html is not None:
            return html
        logger.info("agent.browser.fetch.urllib_fallback url=%s", url)
        return _fetch_html_with_urllib(url)

    def open_url(self, url: str) -> str:
        return self.fetch_html(url)

    def submit_search(
        self,
        entry_url: str,
        query: str,
        *,
        selectors: dict[str, object] | None = None,
        rule_payload: dict[str, object] | None = None,
    ) -> str:
        selectors = selectors or {}
        rule_payload = rule_payload or {}
        search_url = _search_url(entry_url, query, selectors=selectors, rule_payload=rule_payload)
        if self.html_fetcher is not None:
            return self.html_fetcher(search_url)
        html = self._submit_search_with_browser(
            entry_url,
            query,
            selectors=selectors,
            rule_payload=rule_payload,
        )
        if html is not None:
            return html
        logger.info("agent.browser.search.urllib_fallback entry_url=%s query=%s", entry_url, query)
        return _fetch_html_with_urllib(search_url)

    def _fetch_html_with_browser(self, url: str) -> str | None:
        try:
            browser = self._ensure_fetch_browser()
        except Exception as exc:
            logger.warning(
                "agent.browser.fetch.browser_unavailable url=%s failure_kind=%s detail=%s",
                url,
                exc.__class__.__name__,
                exc,
            )
            return None
        if browser is None:
            return None

        fetch_html = getattr(browser, "fetch_html", None)
        if callable(fetch_html):
            logger.info("agent.browser.fetch.fetch_html url=%s", url)
            return str(fetch_html(url))

        open_url = getattr(browser, "open_url", None)
        if callable(open_url):
            logger.info("agent.browser.fetch.open_url url=%s", url)
            opened = open_url(url)
            if isinstance(opened, str):
                return opened

        page = _new_page(browser)
        if page is None:
            return None
        logger.info("agent.browser.page.open url=%s", url)
        try:
            _goto(page, url)
            content = getattr(page, "content", None)
            if not callable(content):
                return None
            return str(content())
        finally:
            close = getattr(page, "close", None)
            if callable(close):
                close()

    def _ensure_fetch_browser(self) -> Any | None:
        if self._fetch_browser is not None:
            return self._fetch_browser
        profile_path = self.browser_profiles_dir / "public-fetch"
        profile_path.mkdir(parents=True, exist_ok=True)
        browser = self.browser_factory(profile_path)
        if hasattr(browser, "profile_path"):
            setattr(browser, "profile_path", profile_path)
        self._fetch_browser = browser
        return browser

    def _submit_search_with_browser(
        self,
        entry_url: str,
        query: str,
        *,
        selectors: dict[str, object],
        rule_payload: dict[str, object],
    ) -> str | None:
        try:
            browser = self._ensure_fetch_browser()
        except Exception as exc:
            logger.warning(
                "agent.browser.search.browser_unavailable entry_url=%s query=%s failure_kind=%s detail=%s",
                entry_url,
                query,
                exc.__class__.__name__,
                exc,
            )
            return None
        if browser is None:
            return None

        submit_search = getattr(browser, "submit_search", None)
        if callable(submit_search):
            return str(submit_search(entry_url, query, selectors=selectors, rule_payload=rule_payload))

        return _submit_search_on_browser(browser, entry_url, query, selectors=selectors, rule_payload=rule_payload)


class _CamoufoxBrowser:
    def __init__(self, profile_path: Path) -> None:
        try:
            from camoufox.sync_api import Camoufox  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "camoufox is required to launch the Agent browser runtime; "
                "install the project browser dependencies before starting the Agent"
            ) from exc

        self.profile_path = profile_path
        self._launcher = Camoufox(
            persistent_context=True,
            user_data_dir=str(profile_path),
            headless=False,
            locale=DEFAULT_CAMOUFOX_LOCALE,
            window=DEFAULT_CAMOUFOX_WINDOW,
            fonts=list(DEFAULT_CAMOUFOX_FONTS),
        )
        self._context = self._launcher.__enter__()

    def fetch_html(self, url: str) -> str:
        return self.open_url(url)

    def open_url(self, url: str) -> str:
        page = self.new_page()
        _goto(page, url)
        content = getattr(page, "content", None)
        return str(content()) if callable(content) else ""

    def submit_search(
        self,
        entry_url: str,
        query: str,
        *,
        selectors: dict[str, object] | None = None,
        rule_payload: dict[str, object] | None = None,
    ) -> str:
        return _submit_search_on_browser(
            self,
            entry_url,
            query,
            selectors=selectors or {},
            rule_payload=rule_payload or {},
        ) or ""

    def new_page(self) -> Any:
        page = _resolve_existing_page(self._context)
        if page is not None:
            return page
        new_page = getattr(self._context, "new_page", None)
        if not callable(new_page):
            raise RuntimeError("camoufox context does not support new_page")
        return new_page()

    def close(self) -> None:
        self._launcher.__exit__(None, None, None)


def _launch_camoufox_browser(profile_path: Path) -> _CamoufoxBrowser:
    return _CamoufoxBrowser(profile_path)


def _open_initial_url(browser: Any, url: str) -> None:
    open_url = getattr(browser, "open_url", None)
    if callable(open_url):
        open_url(url)
        return
    page = _new_page(browser)
    if page is not None:
        _goto(page, url)


def _submit_search_on_browser(
    browser: Any,
    entry_url: str,
    query: str,
    *,
    selectors: dict[str, object],
    rule_payload: dict[str, object],
) -> str | None:
    page = _new_page(browser)
    if page is None:
        return None

    search_input_selector = _string_value(selectors.get("search_input_selector"))
    search_button_selector = _string_value(selectors.get("search_button_selector"))
    if not search_input_selector:
        _goto(page, _search_url(entry_url, query, selectors=selectors, rule_payload=rule_payload))
    else:
        _goto(page, entry_url)
        _fill(page, search_input_selector, query)
        if search_button_selector:
            _click(page, search_button_selector)
        else:
            _press(page, search_input_selector, "Enter")

    wait_selector = _string_value(selectors.get("search_result_wait_selector"))
    if wait_selector:
        _wait_for_selector(page, wait_selector)

    content = getattr(page, "content", None)
    if not callable(content):
        return None
    return str(content())


def _ensure_browser_alive(browser: Any) -> None:
    is_closed = getattr(browser, "is_closed", None)
    if callable(is_closed) and bool(is_closed()):
        raise RuntimeError("browser session is closed")

    context = getattr(browser, "_context", None)
    if context is not None and _object_reports_closed(context):
        raise RuntimeError("browser session is closed")


def _resolve_existing_page(context: Any) -> Any | None:
    pages = getattr(context, "pages", None)
    if isinstance(pages, list) and pages:
        return pages[0]
    if callable(pages):
        resolved = pages()
        if isinstance(resolved, list) and resolved:
            return resolved[0]
    return None


def _new_page(browser: Any) -> Any | None:
    new_page = getattr(browser, "new_page", None)
    if callable(new_page):
        return new_page()
    goto = getattr(browser, "goto", None)
    content = getattr(browser, "content", None)
    if callable(goto) and callable(content):
        return browser
    return None


def _goto(page: Any, url: str) -> None:
    goto = getattr(page, "goto", None)
    if not callable(goto):
        raise RuntimeError("browser page does not support goto")
    try:
        goto(url, wait_until="networkidle")
    except TypeError:
        goto(url)


def _fill(page: Any, selector: str, value: str) -> None:
    fill = getattr(page, "fill", None)
    if callable(fill):
        fill(selector, value)
        return
    locator = getattr(page, "locator", None)
    if callable(locator):
        field = locator(selector)
        field_fill = getattr(field, "fill", None)
        if callable(field_fill):
            field_fill(value)
            return
    raise RuntimeError("browser page does not support fill")


def _click(page: Any, selector: str) -> None:
    click = getattr(page, "click", None)
    if callable(click):
        click(selector)
        return
    locator = getattr(page, "locator", None)
    if callable(locator):
        target = locator(selector)
        target_click = getattr(target, "click", None)
        if callable(target_click):
            target_click()
            return
    raise RuntimeError("browser page does not support click")


def _press(page: Any, selector: str, key: str) -> None:
    press = getattr(page, "press", None)
    if callable(press):
        press(selector, key)
        return
    locator = getattr(page, "locator", None)
    if callable(locator):
        target = locator(selector)
        target_press = getattr(target, "press", None)
        if callable(target_press):
            target_press(key)
            return
    raise RuntimeError("browser page does not support press")


def _wait_for_selector(page: Any, selector: str) -> None:
    wait_for_selector = getattr(page, "wait_for_selector", None)
    if callable(wait_for_selector):
        wait_for_selector(selector)


def _search_url(
    entry_url: str,
    query: str,
    *,
    selectors: dict[str, object],
    rule_payload: dict[str, object],
) -> str:
    search_policy = rule_payload.get("search_policy")
    query_param = str(
        rule_payload.get("search_query_param")
        or selectors.get("search_query_param")
        or (search_policy.get("query_param") if isinstance(search_policy, dict) else None)
        or "q"
    )
    parts = urlsplit(entry_url)
    params = dict(parse_qsl(parts.query, keep_blank_values=True))
    params[query_param] = query
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), parts.fragment))


def _string_value(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _fetch_html_with_urllib(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 OpportunityCrawler/0.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        content_type = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(content_type, errors="replace")


def _object_reports_closed(candidate: Any) -> bool:
    is_closed = getattr(candidate, "is_closed", None)
    if not callable(is_closed):
        return False
    try:
        return bool(is_closed())
    except Exception as exc:
        message = str(exc).lower()
        return any(
            token in message
            for token in (
                "target page, context or browser has been closed",
                "browser has been closed",
                "context closed",
                "page closed",
            )
        )
