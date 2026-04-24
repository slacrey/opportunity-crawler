from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin


@dataclass
class HtmlNode:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list["HtmlNode"] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)

    def text_content(self) -> str:
        parts = list(self.text_parts)
        for child in self.children:
            parts.append(child.text_content())
        return " ".join(" ".join(parts).split())


class _MiniHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = HtmlNode("document")
        self._stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = HtmlNode(tag=tag.lower(), attrs={key: value or "" for key, value in attrs})
        self._stack[-1].children.append(node)
        self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = HtmlNode(tag=tag.lower(), attrs={key: value or "" for key, value in attrs})
        self._stack[-1].children.append(node)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        while len(self._stack) > 1:
            node = self._stack.pop()
            if node.tag == tag:
                break

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self._stack[-1].text_parts.append(text)


def parse_list_items(
    html: str,
    *,
    selectors: dict[str, str],
    base_url: str,
) -> list[dict[str, Any]]:
    root = parse_html(html)
    list_selector = selectors.get("list_selector", "")
    link_selector = selectors.get("detail_link_selector", "a")
    date_selector = selectors.get("published_at_selector", "")

    rows: list[dict[str, Any]] = []
    for item in find_nodes(root, list_selector):
        link = first_node(item, link_selector)
        if link is None:
            continue
        href = link.attrs.get("href", "")
        url = urljoin(base_url, href) if href else base_url
        row: dict[str, Any] = {
            "title": link.text_content(),
            "url": url,
        }
        if date_selector:
            date_node = first_node(item, date_selector)
            if date_node is not None:
                row["published_at"] = date_node.text_content()
        rows.append(row)
    return rows


def extract_text_by_selector(html: str, selector: str) -> str:
    if not selector:
        return ""
    node = first_node(parse_html(html), selector)
    return node.text_content() if node is not None else ""


def parse_html(html: str) -> HtmlNode:
    parser = _MiniHtmlParser()
    parser.feed(html)
    parser.close()
    return parser.root


def first_node(root: HtmlNode, selector: str) -> HtmlNode | None:
    nodes = find_nodes(root, selector)
    return nodes[0] if nodes else None


def find_nodes(root: HtmlNode, selector: str) -> list[HtmlNode]:
    if not selector:
        return []
    return [node for node in _walk(root) if _matches(node, selector)]


def _walk(node: HtmlNode) -> list[HtmlNode]:
    nodes = [node]
    for child in node.children:
        nodes.extend(_walk(child))
    return nodes


def _matches(node: HtmlNode, selector: str) -> bool:
    selector = selector.strip()
    if not selector:
        return False
    if selector.startswith("."):
        return selector[1:] in node.attrs.get("class", "").split()
    if selector.startswith("#"):
        return node.attrs.get("id") == selector[1:]
    if "." in selector:
        tag, class_name = selector.split(".", 1)
        return node.tag == tag.lower() and class_name in node.attrs.get("class", "").split()
    return node.tag == selector.lower()

