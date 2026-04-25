from __future__ import annotations

from collections.abc import Iterator
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

from opportunity_crawler.collection.adapters.base import BaseAdapter, CollectionResult
from opportunity_crawler.collection.parsing import extract_text_by_selector, parse_list_items
from opportunity_crawler.shared.contracts.agent_protocol import CollectionCommandMessage


class PublicSearchListDetailAdapter(BaseAdapter):
    mode = "public_search_list_detail"

    def collect(self, context: dict[str, object]) -> CollectionResult:
        command = context.get("command")
        if not isinstance(command, CollectionCommandMessage):
            raise TypeError("public source collection requires a CollectionCommandMessage")
        rule_payload = command.rule_payload or command.draft_rule_payload or {}
        entry_url = str(rule_payload.get("entry_url") or "")
        if not entry_url:
            raise ValueError("public source collection requires rule_payload.entry_url")

        selectors = _dict(rule_payload.get("selectors"))
        pagination_policy = _dict(rule_payload.get("pagination_policy"))
        max_items = _positive_int(pagination_policy.get("max_items"))
        browser_runtime = context.get("browser_runtime")

        query_strings = _query_strings(rule_payload.get("query_profile"))
        list_rows: list[dict[str, object]] = []
        seen_urls: set[str] = set()
        total_list_item_count = 0
        list_page_count = 0
        for query, list_html in _iter_list_pages(
            browser_runtime,
            entry_url=entry_url,
            queries=query_strings,
            selectors=selectors,
            rule_payload=rule_payload,
        ):
            list_page_count += 1
            parsed_rows = parse_list_items(list_html, selectors=selectors, base_url=entry_url)
            total_list_item_count += len(parsed_rows)
            for row in parsed_rows:
                url = str(row.get("url") or "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                if query is not None:
                    row["query_keywords"] = query
                list_rows.append(row)
                if max_items is not None and len(list_rows) >= max_items:
                    break
            if max_items is not None and len(list_rows) >= max_items:
                break
        selected_rows = list_rows[:max_items] if max_items is not None else list_rows
        rows: list[dict[str, object]] = []
        item_failures: list[dict[str, object]] = []
        content_selector = str(selectors.get("content_selector") or "")

        for row in selected_rows:
            detail_url = str(row.get("url") or "")
            try:
                detail_html = _fetch_html(browser_runtime, detail_url)
            except Exception as exc:
                item_failures.append({"url": detail_url, "failure_kind": exc.__class__.__name__, "detail": str(exc)})
                continue
            raw_text = extract_text_by_selector(detail_html, content_selector)
            if not raw_text:
                item_failures.append({"url": detail_url, "failure_kind": "parse_failed"})
                continue
            rows.append({**row, "raw_text": raw_text, "source_item_key": detail_url})

        if not list_rows:
            stop_reason = "empty_result"
        elif max_items is not None and total_list_item_count > max_items:
            stop_reason = "max_items_reached"
        else:
            stop_reason = "completed"
        return CollectionResult(
            rows=rows,
            item_failures=item_failures,
            page_count=max(1, list_page_count),
            diagnostic_snapshot={
                "adapter_mode": self.mode,
                "entry_url": entry_url,
                "list_item_count": total_list_item_count,
                "collected_item_count": len(rows),
                "item_failure_count": len(item_failures),
                "pagination_stop_reason": stop_reason,
                "browser_runtime_present": browser_runtime is not None,
                "query_count": len(query_strings),
                "submitted_queries": query_strings,
            },
        )

    def collect_from_fixtures(
        self,
        *,
        list_html: str,
        detail_pages: dict[str, str],
        base_url: str,
        selectors: dict[str, str],
    ) -> CollectionResult:
        list_rows = parse_list_items(list_html, selectors=selectors, base_url=base_url)
        rows: list[dict[str, object]] = []
        item_failures: list[dict[str, object]] = []
        for row in list_rows:
            detail_html = detail_pages.get(str(row["url"]))
            if detail_html is None:
                item_failures.append({"url": row["url"], "failure_kind": "detail_missing"})
                continue
            content = extract_text_by_selector(detail_html, selectors.get("content_selector", ""))
            if not content:
                item_failures.append({"url": row["url"], "failure_kind": "parse_failed"})
                continue
            rows.append({**row, "raw_text": content, "source_item_key": row["url"]})
        return CollectionResult(
            rows=rows,
            item_failures=item_failures,
            page_count=1,
            diagnostic_snapshot={
                "pagination_stop_reason": "fixture_complete",
                "item_failure_count": len(item_failures),
            },
        )


def _fetch_html(browser_runtime: object, url: str) -> str:
    fetch_html = getattr(browser_runtime, "fetch_html", None)
    if callable(fetch_html):
        return str(fetch_html(url))

    open_url = getattr(browser_runtime, "open_url", None)
    if callable(open_url):
        return str(open_url(url))

    raise RuntimeError("browser runtime does not support fetch_html or open_url")


def _iter_list_pages(
    browser_runtime: object,
    *,
    entry_url: str,
    queries: list[str],
    selectors: dict[str, object],
    rule_payload: dict[str, object],
) -> Iterator[tuple[str | None, str]]:
    if not queries:
        yield None, _fetch_html(browser_runtime, entry_url)
        return

    for query in queries:
        yield (
            query,
            _submit_search(browser_runtime, entry_url=entry_url, query=query, selectors=selectors, rule_payload=rule_payload),
        )


def _submit_search(
    browser_runtime: object,
    *,
    entry_url: str,
    query: str,
    selectors: dict[str, object],
    rule_payload: dict[str, object],
) -> str:
    submit_search = getattr(browser_runtime, "submit_search", None)
    if callable(submit_search):
        return str(submit_search(entry_url, query, selectors=selectors, rule_payload=rule_payload))
    return _fetch_html(browser_runtime, _search_url(entry_url, query, selectors=selectors, rule_payload=rule_payload))


def _search_url(
    entry_url: str,
    query: str,
    *,
    selectors: dict[str, object],
    rule_payload: dict[str, object],
) -> str:
    query_param = str(
        rule_payload.get("search_query_param")
        or selectors.get("search_query_param")
        or _dict(rule_payload.get("search_policy")).get("query_param")
        or "q"
    )
    parts = urlsplit(entry_url)
    params = dict(parse_qsl(parts.query, keep_blank_values=True))
    params[query_param] = query
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), parts.fragment))


def _query_strings(value: object) -> list[str]:
    profile = _dict(value)
    queries = profile.get("queries")
    if not isinstance(queries, list):
        return []
    return [str(query).strip() for query in queries if str(query).strip()]


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _positive_int(value: object) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None
