from __future__ import annotations

import hashlib
from typing import Any


def build_evidence_payload(row: dict[str, Any]) -> dict[str, Any]:
    raw_text = str(row.get("raw_text") or "")
    source_item_key = row.get("source_item_key") or row.get("url")
    content_fingerprint = row.get("content_fingerprint") or hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    return {
        **row,
        "source_item_key": source_item_key,
        "content_fingerprint": content_fingerprint,
    }

