from __future__ import annotations

from pathlib import Path

from tests.integration.api_helpers import auth_headers, build_client, first_source_id

from opportunity_crawler.shared.db.base import connect_sqlite


def test_control_panel_query_endpoints_require_authentication(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.get("/api/dashboard/summary")

    assert response.status_code == 401


def test_auth_me_returns_current_profile_and_rejects_missing_session(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    headers = auth_headers(client)

    current = client.get("/api/auth/me", headers=headers)
    missing = client.get("/api/auth/me", headers={"Authorization": "Bearer expired-token"})

    assert current.status_code == 200, current.text
    assert current.json()["user"]["username"] == "admin"
    assert "administrator" in current.json()["user"]["roles"]
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "not_authenticated"


def test_dashboard_summary_reads_real_control_panel_counts(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    headers = auth_headers(client)
    source_id = first_source_id(client, headers, name="微信公众号手动导入")
    candidate_id = _create_candidate(client, headers, source_id)
    client.post(f"/api/opportunities/{candidate_id}/review", headers=headers, json={"review_status": "accepted"})
    _seed_collection_run(client.app.state.database_path, source_id)
    _seed_agent(client.app.state.database_path)

    response = client.get("/api/dashboard/summary", headers=headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["sources"]["total"] >= 1
    assert payload["opportunities"]["accepted"] == 1
    assert payload["runs"]["failed"] == 1
    assert payload["agents"]["online"] == 1


def test_opportunity_list_and_detail_return_related_source_evidence_and_analysis(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    headers = auth_headers(client)
    source_id = first_source_id(client, headers, name="微信公众号手动导入")
    candidate_id = _create_candidate(client, headers, source_id)

    listing = client.get("/api/opportunities?review_status=pending", headers=headers)
    detail = client.get(f"/api/opportunities/{candidate_id}", headers=headers)

    assert listing.status_code == 200, listing.text
    assert listing.json()["items"][0]["id"] == candidate_id
    assert listing.json()["items"][0]["source_name"] == "微信公众号手动导入"
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["candidate"]["id"] == candidate_id
    assert payload["source"]["id"] == source_id
    assert payload["evidence"]["title"] == "昆山 AI 云平台采购意向"
    assert "extracted_facts" in payload["analysis"]


def test_missing_control_panel_details_return_not_found(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    headers = auth_headers(client)

    opportunity = client.get("/api/opportunities/999999", headers=headers)
    source = client.get("/api/sources/999999", headers=headers)

    assert opportunity.status_code == 404
    assert source.status_code == 404


def test_source_detail_and_advanced_rules_include_business_rule_state(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    headers = auth_headers(client)
    source_id = first_source_id(client, headers, name="中国政府采购网")
    payload = {
        "adapter_mode": "public_search_list_detail",
        "entry_url": "https://www.ccgp.gov.cn",
        "login_mode": "not_required",
        "selectors": {
            "list_selector": ".result",
            "detail_link_selector": "a",
            "content_selector": ".content",
        },
    }
    created = client.post(f"/api/sources/{source_id}/advanced-rules", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    version = created.json()["version"]
    client.post(f"/api/sources/{source_id}/advanced-rules/{version}/activate", headers=headers)

    detail = client.get(f"/api/sources/{source_id}", headers=headers)
    versions = client.get(f"/api/sources/{source_id}/advanced-rules", headers=headers)

    assert detail.status_code == 200, detail.text
    assert detail.json()["source"]["id"] == source_id
    assert detail.json()["basic_rules"]["frequency"] == "daily"
    assert detail.json()["active_rule"]["version"] == version
    assert versions.status_code == 200, versions.text
    assert versions.json()["items"][0]["status"] == "active"
    assert versions.json()["items"][0]["selectors"]["list_selector"] == ".result"


def test_operational_lists_return_real_rows(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    headers = auth_headers(client)
    source_id = first_source_id(client, headers, name="微信公众号手动导入")
    candidate_id = _create_candidate(client, headers, source_id)
    client.post(f"/api/opportunities/{candidate_id}/review", headers=headers, json={"review_status": "accepted"})
    client.post("/api/notifications/dingtalk/digest", headers=headers, json={"simulate_failure": True})
    _seed_collection_run(client.app.state.database_path, source_id)
    _seed_agent(client.app.state.database_path)

    runs = client.get("/api/collection-runs", headers=headers)
    agents = client.get("/api/agents", headers=headers)
    notifications = client.get("/api/notifications/logs", headers=headers)
    audit = client.get("/api/audit-logs", headers=headers)
    customers = client.get("/api/customers", headers=headers)

    assert runs.status_code == 200, runs.text
    assert runs.json()["items"][0]["run_id"] == "run-control-panel"
    assert agents.status_code == 200, agents.text
    assert agents.json()["items"][0]["agent_id"] == "agent-control-panel"
    assert notifications.status_code == 200, notifications.text
    assert notifications.json()["items"][0]["status"] == "failed"
    assert audit.status_code == 200, audit.text
    assert any(row["action"] == "opportunity.review" for row in audit.json()["items"])
    assert customers.status_code == 200, customers.text
    assert customers.json()["items"][0]["name"] == "昆山某单位"


def _create_candidate(client, headers: dict[str, str], source_id: int) -> int:
    response = client.post(
        "/api/opportunities/manual-import",
        headers=headers,
        json={
            "source_id": source_id,
            "title": "昆山 AI 云平台采购意向",
            "url": "https://example.test/control-panel/1",
            "body": "昆山 制造业 AI 云平台 数字化转型采购意向",
            "organization_name": "昆山某单位",
            "region": "昆山",
            "industry": "制造业",
            "project_stage": "采购意向",
            "budget_amount": 5000000,
        },
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def _seed_collection_run(database_path: Path, source_id: int) -> None:
    with connect_sqlite(database_path) as connection:
        connection.execute(
            """
            INSERT INTO collection_runs (
                run_id, source_id, rule_version, status, item_count, failure_kind, diagnostic_snapshot_json
            )
            VALUES ('run-control-panel', ?, 1, 'failed', 3, 'parse_failed', '{"reason":"fixture"}')
            """,
            (source_id,),
        )
        connection.commit()


def _seed_agent(database_path: Path) -> None:
    with connect_sqlite(database_path) as connection:
        connection.execute(
            """
            INSERT INTO agent_hosts (host_id, hostname, platform, app_version, last_seen_at)
            VALUES ('host-control-panel', 'localhost', 'darwin', '0.1.0', CURRENT_TIMESTAMP)
            """,
        )
        connection.execute(
            """
            INSERT INTO agent_instances (agent_id, host_id, status, capacity, active_sessions, last_heartbeat_at)
            VALUES ('agent-control-panel', 'host-control-panel', 'online', 2, 1, CURRENT_TIMESTAMP)
            """,
        )
        connection.commit()
