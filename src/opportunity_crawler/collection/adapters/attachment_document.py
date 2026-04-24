from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from opportunity_crawler.collection.adapters.base import BaseAdapter, CollectionResult
from opportunity_crawler.collection.adapters.public_search_list_detail import _dict, _fetch_html
from opportunity_crawler.collection.parsing import extract_text_by_selector, find_nodes, first_node, parse_html
from opportunity_crawler.shared.contracts.agent_protocol import CollectionCommandMessage


class AttachmentDocumentAdapter(BaseAdapter):
    mode = "attachment_document"

    def collect(self, context: dict[str, object]) -> CollectionResult:
        command = context.get("command")
        if not isinstance(command, CollectionCommandMessage):
            raise TypeError("attachment collection requires a CollectionCommandMessage")
        rule_payload = command.rule_payload or command.draft_rule_payload or {}
        entry_url = str(rule_payload.get("entry_url") or "")
        if not entry_url:
            raise ValueError("attachment collection requires rule_payload.entry_url")

        selectors = _dict(rule_payload.get("selectors"))
        attachment_policy = _dict(rule_payload.get("attachment_policy"))
        browser_runtime = context.get("browser_runtime")
        entry_html = _fetch_html(browser_runtime, entry_url)
        attachment_links = _attachment_links(
            entry_html,
            base_url=entry_url,
            selector=str(attachment_policy.get("attachment_selector") or selectors.get("attachment_selector") or "a"),
        )

        title = extract_text_by_selector(entry_html, str(selectors.get("title_selector") or "")) or entry_url
        published_at = extract_text_by_selector(entry_html, str(selectors.get("published_at_selector") or ""))
        summary = extract_text_by_selector(entry_html, str(selectors.get("content_selector") or ""))
        rows: list[dict[str, Any]] = []
        item_failures: list[dict[str, Any]] = []

        for attachment in attachment_links:
            attachment_url = str(attachment["url"])
            try:
                attachment_text = _fetch_html(browser_runtime, attachment_url).strip()
            except Exception as exc:
                item_failures.append(
                    {"url": attachment_url, "failure_kind": exc.__class__.__name__, "detail": str(exc)}
                )
                continue

            raw_text = "\n\n".join(part for part in (summary, attachment_text) if part)
            row: dict[str, Any] = {
                "title": title,
                "url": entry_url,
                "raw_text": raw_text,
                "source_item_key": attachment_url,
                "attachments": [
                    {
                        "name": attachment["name"],
                        "url": attachment_url,
                        "content_type": "text",
                    }
                ],
            }
            if published_at:
                row["published_at"] = published_at
            rows.append(row)

        stop_reason = "empty_result" if not attachment_links else "completed"
        return CollectionResult(
            rows=rows,
            item_failures=item_failures,
            page_count=1,
            diagnostic_snapshot={
                "adapter_mode": self.mode,
                "entry_url": entry_url,
                "attachment_count": len(attachment_links),
                "collected_item_count": len(rows),
                "item_failure_count": len(item_failures),
                "pagination_stop_reason": stop_reason,
                "browser_runtime_present": browser_runtime is not None,
            },
        )


def _attachment_links(html: str, *, base_url: str, selector: str) -> list[dict[str, str]]:
    root = parse_html(html)
    links: list[dict[str, str]] = []
    for node in find_nodes(root, selector):
        link = node if node.tag == "a" else first_node(node, "a")
        if link is None:
            continue
        href = link.attrs.get("href")
        if not href:
            continue
        links.append(
            {
                "name": link.text_content() or href.rsplit("/", 1)[-1],
                "url": urljoin(base_url, href),
            }
        )
    return links
