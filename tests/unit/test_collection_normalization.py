from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.collection.normalization import apply_normalization_mapping


def test_apply_normalization_mapping_maps_source_fields_to_candidate_fields() -> None:
    normalized = apply_normalization_mapping(
        {"headline": "昆山项目", "buyer": "昆山某单位"},
        {"title": "headline", "organization_name": "buyer"},
    )

    assert normalized == {"title": "昆山项目", "organization_name": "昆山某单位"}

