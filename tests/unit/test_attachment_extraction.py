from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.collection.attachments import extract_attachment_text


def test_extract_attachment_text_reads_text_fixture(tmp_path: Path) -> None:
    path = tmp_path / "notice.txt"
    path.write_text("附件正文：数字化转型项目", encoding="utf-8")

    result = extract_attachment_text(path)

    assert result["file_name"] == "notice.txt"
    assert result["text"] == "附件正文：数字化转型项目"

