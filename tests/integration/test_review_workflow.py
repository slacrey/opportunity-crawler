from __future__ import annotations

from pathlib import Path

from tests.integration.api_helpers import auth_headers, build_client, first_source_id


def test_review_workflow_updates_follow_up_and_customer_history(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    headers = auth_headers(client)
    source_id = first_source_id(client, headers, name="微信公众号手动导入")

    created = client.post(
        "/api/opportunities/manual-import",
        headers=headers,
        json={
            "source_id": source_id,
            "title": "昆山 AI 云平台采购意向",
            "url": "https://example.test/review/1",
            "body": "昆山 制造业 AI 云平台 数字化转型",
            "organization_name": "昆山某单位",
            "region": "昆山",
            "industry": "制造业",
            "project_stage": "采购意向",
            "budget_amount": 5000000,
        },
    )
    assert created.status_code == 201, created.text
    candidate_id = created.json()["id"]

    accepted = client.post(
        f"/api/opportunities/{candidate_id}/review",
        headers=headers,
        json={"review_status": "accepted"},
    )
    assert accepted.status_code == 200, accepted.text

    follow_up = client.post(
        f"/api/opportunities/{candidate_id}/follow-up",
        headers=headers,
        json={"follow_up_status": "visited", "note": "已完成首次拜访"},
    )
    assert follow_up.status_code == 200, follow_up.text
    assert follow_up.json()["follow_up_status"] == "visited"

    history = client.get("/api/customers/昆山某单位/history", headers=headers)
    assert history.status_code == 200, history.text
    assert history.json()["opportunity_count"] == 1
    assert history.json()["activities"][0]["activity_type"] == "visited"

