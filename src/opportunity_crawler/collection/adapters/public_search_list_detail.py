from __future__ import annotations

from opportunity_crawler.collection.adapters.base import BaseAdapter, CollectionResult
from opportunity_crawler.collection.parsing import extract_text_by_selector, parse_list_items


class PublicSearchListDetailAdapter(BaseAdapter):
    mode = "public_search_list_detail"

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

