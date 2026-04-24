from __future__ import annotations

import hashlib
import re


class DedupeService:
    def build_dedupe_key(
        self,
        *,
        source_id: int,
        source_item_key: str | None,
        url: str | None,
        title: str,
        organization_name: str | None,
        published_at: str | None,
        content_fingerprint: str | None,
    ) -> str:
        if source_item_key:
            identity = f"source_item:{source_id}:{source_item_key.strip()}"
        elif url:
            identity = f"url:{source_id}:{url.strip()}"
        elif content_fingerprint:
            identity = f"fingerprint:{source_id}:{content_fingerprint.strip()}"
        else:
            identity = "title_org_date:{}:{}:{}:{}".format(
                source_id,
                _normalize(title),
                _normalize(organization_name or ""),
                published_at or "",
            )
        return _sha256(identity)

    def build_project_association_key(
        self,
        *,
        source_id: int,
        title: str,
        organization_name: str | None,
    ) -> str:
        base_title = _normalize_project_title(title)
        return _sha256(f"project:{source_id}:{_normalize(organization_name or '')}:{base_title}")


def _normalize(value: str) -> str:
    return "".join(value.lower().split())


def _normalize_project_title(value: str) -> str:
    normalized = _normalize(value)
    for stage_word in ("采购意向", "招标计划", "招标公告", "中标公告", "成交公告", "结果公告", "合同公告"):
        normalized = normalized.replace(stage_word, "")
    normalized = re.sub(r"[：:（）()\\[\\]【】]", "", normalized)
    return normalized


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

