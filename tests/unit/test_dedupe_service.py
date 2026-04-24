from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.control_plane.services.dedupe_service import DedupeService


def test_dedupe_service_prefers_source_item_key_for_stable_candidate_keys() -> None:
    service = DedupeService()

    first = service.build_dedupe_key(
        source_id=1,
        source_item_key="https://example.test/project/1",
        url="https://example.test/project/1?utm=ignored",
        title="昆山智慧城市项目",
        organization_name="昆山某单位",
        published_at="2026-04-24",
        content_fingerprint="aaa",
    )
    second = service.build_dedupe_key(
        source_id=1,
        source_item_key="https://example.test/project/1",
        url="https://example.test/project/1?from=list",
        title="不同标题",
        organization_name=None,
        published_at=None,
        content_fingerprint="bbb",
    )

    assert first == second


def test_dedupe_service_keeps_later_project_stage_association_key_separate_from_exact_key() -> None:
    service = DedupeService()

    association_key = service.build_project_association_key(
        source_id=1,
        title="昆山智慧城市项目中标公告",
        organization_name="昆山某单位",
    )

    assert association_key == service.build_project_association_key(
        source_id=1,
        title="昆山智慧城市项目采购意向",
        organization_name="昆山某单位",
    )

