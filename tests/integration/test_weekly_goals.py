from __future__ import annotations

from pathlib import Path

from tests.integration.api_helpers import auth_headers, build_client, first_source_id


def test_weekly_goal_progress_aggregates_visits_quotes_and_accepted_opportunities(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    headers = auth_headers(client)
    source_id = first_source_id(client, headers, name="微信公众号手动导入")

    created = client.post(
        "/api/opportunities/manual-import",
        headers=headers,
        json={
            "source_id": source_id,
            "title": "昆山 AI 项目",
            "body": "昆山 AI 云平台",
            "organization_name": "昆山某单位",
            "region": "昆山",
            "industry": "制造业",
        },
    )
    candidate_id = created.json()["id"]
    client.post(f"/api/opportunities/{candidate_id}/review", headers=headers, json={"review_status": "accepted"})
    client.post(f"/api/opportunities/{candidate_id}/follow-up", headers=headers, json={"follow_up_status": "visited"})
    client.post(f"/api/opportunities/{candidate_id}/follow-up", headers=headers, json={"follow_up_status": "quoted"})

    response = client.get("/api/goals/weekly-progress?week_start=2026-04-20", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["accepted_opportunities"] == 1
    assert response.json()["visits"] == 1
    assert response.json()["quotes"] == 1

