from __future__ import annotations

from typing import Any, Callable
import re


class DingTalkTransportError(Exception):
    pass


class DingTalkDigestBuilder:
    def build_daily_digest(self, candidates: list[dict[str, Any]]) -> str:
        if not candidates:
            return "今日暂无高优先级商机。"
        lines = ["今日高优先级商机摘要"]
        for candidate in candidates:
            organization = candidate.get("organization_name") or "未知客户"
            phone = candidate.get("contact_phone")
            phone_text = f" 联系方式：{_mask_phone(str(phone))}" if phone else ""
            lines.append(
                "- [{} {}分] {} / {}{}".format(
                    candidate.get("priority_label", "P?"),
                    candidate.get("score", 0),
                    candidate.get("title", ""),
                    organization,
                    phone_text,
                )
            )
        return "\n".join(lines)


class DingTalkClient:
    def __init__(self, transport: Callable[[str], None] | None = None) -> None:
        self.transport = transport or (lambda message: None)

    def send_message(self, message: str) -> None:
        self.transport(message)


def _mask_phone(value: str) -> str:
    return re.sub(r"(\d{3})\d{4}(\d{4})", r"\1****\2", value)

