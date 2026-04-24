from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.collection.adapters.manual_import import ManualImportAdapter


def test_manual_import_adapter_creates_evidence_payload() -> None:
    adapter = ManualImportAdapter()

    result = adapter.collect(
        {
            "title": "微信公众号商机",
            "url": "https://example.test/wx",
            "body": "昆山 AI 数字化转型",
            "source_name": "微信公众号手动导入",
        }
    )

    assert result.item_count == 1
    assert result.rows[0]["title"] == "微信公众号商机"
    assert result.rows[0]["source_item_key"] == "https://example.test/wx"
