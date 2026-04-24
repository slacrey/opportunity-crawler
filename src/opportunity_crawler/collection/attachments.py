from __future__ import annotations

from pathlib import Path


def extract_attachment_text(path: str | Path) -> dict[str, str]:
    attachment_path = Path(path)
    return {
        "file_name": attachment_path.name,
        "text": attachment_path.read_text(encoding="utf-8"),
    }

