from __future__ import annotations

import json
from typing import Any
from urllib.parse import urljoin
from xml.etree import ElementTree

from opportunity_crawler.collection.adapters.base import BaseAdapter, CollectionResult
from opportunity_crawler.collection.adapters.public_search_list_detail import _dict, _fetch_html, _positive_int
from opportunity_crawler.collection.normalization import apply_normalization_mapping
from opportunity_crawler.shared.contracts.agent_protocol import CollectionCommandMessage


class ApiOrFeedAdapter(BaseAdapter):
    mode = "api_or_feed"

    def collect(self, context: dict[str, object]) -> CollectionResult:
        command = context.get("command")
        if not isinstance(command, CollectionCommandMessage):
            raise TypeError("api/feed collection requires a CollectionCommandMessage")
        rule_payload = command.rule_payload or command.draft_rule_payload or {}
        entry_url = str(rule_payload.get("entry_url") or "")
        if not entry_url:
            raise ValueError("api/feed collection requires rule_payload.entry_url")

        browser_runtime = context.get("browser_runtime")
        raw_payload = _fetch_html(browser_runtime, entry_url)
        parsed_items, source_format = _parse_items(raw_payload)
        pagination_policy = _dict(rule_payload.get("pagination_policy"))
        max_items = _positive_int(command.max_items) or _positive_int(pagination_policy.get("max_items"))
        selected_items = parsed_items[:max_items] if max_items is not None else parsed_items
        mapping = _string_mapping(rule_payload.get("normalization_mapping"))
        rows = [_normalize_item(item, mapping=mapping, base_url=entry_url) for item in selected_items]

        if not parsed_items:
            stop_reason = "empty_result"
        elif max_items is not None and len(parsed_items) > max_items:
            stop_reason = "max_items_reached"
        else:
            stop_reason = "completed"

        return CollectionResult(
            rows=rows,
            page_count=1,
            diagnostic_snapshot={
                "adapter_mode": self.mode,
                "entry_url": entry_url,
                "source_format": source_format,
                "list_item_count": len(parsed_items),
                "collected_item_count": len(rows),
                "pagination_stop_reason": stop_reason,
                "browser_runtime_present": browser_runtime is not None,
            },
        )


def _parse_items(raw_payload: str) -> tuple[list[dict[str, Any]], str]:
    payload = raw_payload.strip()
    if not payload:
        return [], "empty"
    try:
        return _json_items(json.loads(payload)), "json"
    except json.JSONDecodeError as json_error:
        _ = json_error

    try:
        return _xml_items(payload), "xml"
    except ElementTree.ParseError as exc:
        raise ValueError("api/feed response is not valid JSON or XML") from exc


def _json_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if not isinstance(value, dict):
        return []
    for key in ("items", "data", "results", "rows", "entries"):
        nested = value.get(key)
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
        if isinstance(nested, dict):
            nested_items = _json_items(nested)
            if nested_items:
                return nested_items
    return [value]


def _xml_items(payload: str) -> list[dict[str, Any]]:
    root = ElementTree.fromstring(payload)
    rss_items = [_rss_item(node) for node in root.iter() if _local_name(node.tag) == "item"]
    if rss_items:
        return rss_items
    return [_atom_entry(node) for node in root.iter() if _local_name(node.tag) == "entry"]


def _rss_item(node: ElementTree.Element) -> dict[str, Any]:
    return {
        "id": _child_text(node, "guid"),
        "title": _child_text(node, "title"),
        "url": _child_text(node, "link"),
        "published_at": _child_text(node, "pubDate"),
        "raw_text": _child_text(node, "description"),
    }


def _atom_entry(node: ElementTree.Element) -> dict[str, Any]:
    link = ""
    for child in node:
        if _local_name(child.tag) == "link":
            link = child.attrib.get("href") or (child.text or "")
            break
    return {
        "id": _child_text(node, "id"),
        "title": _child_text(node, "title"),
        "url": link,
        "published_at": _child_text(node, "updated") or _child_text(node, "published"),
        "raw_text": _child_text(node, "summary") or _child_text(node, "content"),
    }


def _normalize_item(item: dict[str, Any], *, mapping: dict[str, str], base_url: str) -> dict[str, Any]:
    mapped = apply_normalization_mapping(item, mapping)
    title = _first_value(mapped, item, ("title", "headline", "name", "subject"))
    url = _first_value(mapped, item, ("url", "link", "href"))
    raw_text = _first_value(mapped, item, ("raw_text", "body", "content", "description", "summary", "text"))
    published_at = _first_value(mapped, item, ("published_at", "published", "pubDate", "date", "updated"))
    source_item_key = _first_value(mapped, item, ("source_item_key", "id", "guid", "key"))
    normalized: dict[str, Any] = {
        **mapped,
        "title": title or str(url or source_item_key or "Untitled API item"),
        "raw_text": raw_text or "",
    }
    if url:
        normalized["url"] = urljoin(base_url, str(url))
    if published_at:
        normalized["published_at"] = str(published_at)
    normalized["source_item_key"] = str(source_item_key or normalized.get("url") or normalized["title"])
    return normalized


def _first_value(mapped: dict[str, Any], item: dict[str, Any], field_names: tuple[str, ...]) -> Any:
    for field_name in field_names:
        value = mapped.get(field_name)
        if value not in (None, ""):
            return value
    for field_name in field_names:
        value = item.get(field_name)
        if value not in (None, ""):
            return value
    return None


def _child_text(node: ElementTree.Element, child_name: str) -> str:
    for child in node:
        if _local_name(child.tag) == child_name:
            return " ".join((child.text or "").split())
    return ""


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _string_mapping(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(field) for key, field in value.items()}
