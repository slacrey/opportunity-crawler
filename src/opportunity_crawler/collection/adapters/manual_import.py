from __future__ import annotations

import hashlib
from typing import Any

from opportunity_crawler.collection.adapters.base import BaseAdapter, CollectionResult


class ManualImportAdapter(BaseAdapter):
    mode = "manual_import"

    def collect(self, payload: dict[str, Any]) -> CollectionResult:
        if "title" not in payload:
            return CollectionResult(
                rows=[],
                diagnostic_snapshot={
                    "adapter_mode": self.mode,
                    "collection_implementation": "manual_payload_required",
                },
            )
        body = str(payload.get("body") or "")
        url = payload.get("url")
        source_item_key = str(url or hashlib.sha256(body.encode("utf-8")).hexdigest())
        row = {
            "title": payload["title"],
            "url": url,
            "raw_text": body,
            "source_name": payload.get("source_name"),
            "source_item_key": source_item_key,
            "content_fingerprint": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        }
        return CollectionResult(rows=[row], page_count=1, diagnostic_snapshot={"mode": self.mode})
