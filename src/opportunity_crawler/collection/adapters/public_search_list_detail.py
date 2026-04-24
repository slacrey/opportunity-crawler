from __future__ import annotations

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

        list_html = _fetch_html(browser_runtime, entry_url)
        list_rows = parse_list_items(list_html, selectors=selectors, base_url=entry_url)
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
        elif max_items is not None and len(list_rows) > max_items:
            stop_reason = "max_items_reached"
        else:
            stop_reason = "completed"
        return CollectionResult(
            rows=rows,
            item_failures=item_failures,
            page_count=1,
            diagnostic_snapshot={
                "adapter_mode": self.mode,
                "entry_url": entry_url,
                "list_item_count": len(list_rows),
                "collected_item_count": len(rows),
                "item_failure_count": len(item_failures),
                "pagination_stop_reason": stop_reason,
                "browser_runtime_present": browser_runtime is not None,
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


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _positive_int(value: object) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None
