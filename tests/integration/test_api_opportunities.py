from __future__ import annotations

from pathlib import Path

from tests.integration.api_helpers import auth_headers, build_client, first_source_id


def test_manual_import_creates_scored_candidate_and_review_updates_status(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    headers = auth_headers(client)
    source_id = first_source_id(client, headers, name="微信公众号手动导入")

    response = client.post(
        "/api/opportunities/manual-import",
        headers=headers,
        json={
            "source_id": source_id,
            "title": "昆山市智慧城市 AI 云平台采购意向",
            "url": "https://example.test/article/1",
            "body": "昆山 制造业 智慧城市 AI 云平台 数字化转型 采购意向",
            "organization_name": "昆山某单位",
            "region": "昆山",
            "industry": "制造业",
            "project_stage": "采购意向",
            "budget_amount": 5000000,
        },
    )

    assert response.status_code == 201, response.text
    candidate = response.json()
    assert candidate["score"] >= 85
    assert candidate["review_status"] == "pending"

    review_response = client.post(
        f"/api/opportunities/{candidate['id']}/review",
        headers=headers,
        json={"review_status": "accepted"},
    )
    assert review_response.status_code == 200
    assert review_response.json()["review_status"] == "accepted"

