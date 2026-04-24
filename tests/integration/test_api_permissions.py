from __future__ import annotations

from pathlib import Path

from tests.integration.api_helpers import auth_headers, build_client, first_source_id


def test_business_user_can_update_basic_rules_but_not_advanced_rules(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    admin_headers = auth_headers(client)
    business_headers = auth_headers(client, username="biz", password="biz-pass")
    source_id = first_source_id(client, admin_headers)

    basic_response = client.patch(
        f"/api/sources/{source_id}/basic-rules",
        headers=business_headers,
        json={"frequency": "weekly", "digest_score_threshold": 80},
    )
    assert basic_response.status_code == 200
    assert basic_response.json()["frequency"] == "weekly"

    advanced_response = client.post(
        f"/api/sources/{source_id}/advanced-rules",
        headers=business_headers,
        json={
            "adapter_mode": "manual_import",
            "entry_url": "manual://test",
            "login_mode": "not_required",
        },
    )
    assert advanced_response.status_code == 403
    assert advanced_response.json()["error"]["code"] == "permission_denied"

