from __future__ import annotations

from pathlib import Path

from tests.integration.api_helpers import auth_headers, build_client, first_source_id


def test_failed_dingtalk_digest_writes_notification_log(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    headers = auth_headers(client)
    source_id = first_source_id(client, headers, name="微信公众号手动导入")

    created = client.post(
        "/api/opportunities/manual-import",
        headers=headers,
        json={
            "source_id": source_id,
            "title": "昆山高优先级项目",
            "body": "昆山 制造业 AI 云平台 数字化转型",
            "organization_name": "昆山某单位",
            "region": "昆山",
            "industry": "制造业",
            "budget_amount": 5000000,
        },
    )
    candidate_id = created.json()["id"]
    client.post(f"/api/opportunities/{candidate_id}/review", headers=headers, json={"review_status": "accepted"})

    response = client.post(
        "/api/notifications/dingtalk/digest",
        headers=headers,
        json={"simulate_failure": True},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "failed"
    assert response.json()["failure_reason"] == "simulated transport failure"
