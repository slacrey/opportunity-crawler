from __future__ import annotations

from pathlib import Path

from tests.integration.api_helpers import auth_headers, build_client, first_source_id


def test_admin_can_create_trial_activate_and_rollback_advanced_rule(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    headers = auth_headers(client)
    source_id = first_source_id(client, headers)

    create_response = client.post(
        f"/api/sources/{source_id}/advanced-rules",
        headers=headers,
        json={
            "adapter_mode": "public_search_list_detail",
            "entry_url": "https://example.test/search",
            "login_mode": "not_required",
            "selectors": {
                "list_selector": ".item",
                "detail_link_selector": "a",
                "content_selector": ".content",
            },
            "pagination_policy": {"max_pages": 2},
        },
    )
    assert create_response.status_code == 201, create_response.text
    version = create_response.json()["version"]
    assert create_response.json()["status"] == "draft"

    trial_response = client.post(
        f"/api/sources/{source_id}/advanced-rules/{version}/trial-run",
        headers=headers,
        json={"max_items": 1},
    )
    assert trial_response.status_code == 200
    assert trial_response.json()["preview_rows"] == []

    activate_response = client.post(
        f"/api/sources/{source_id}/advanced-rules/{version}/activate",
        headers=headers,
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["status"] == "active"

    rollback_response = client.post(
        f"/api/sources/{source_id}/advanced-rules/1/rollback",
        headers=headers,
    )
    assert rollback_response.status_code == 200
    assert rollback_response.json()["version"] == 1
    assert rollback_response.json()["status"] == "active"

