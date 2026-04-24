from __future__ import annotations

from pathlib import Path

from tests.integration.api_helpers import auth_headers, build_client


def test_api_lists_seeded_sources_with_runtime_fields(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    headers = auth_headers(client)

    response = client.get("/api/sources", headers=headers)

    assert response.status_code == 200
    sources = {source["name"]: source for source in response.json()["items"]}
    assert sources["中国政府采购网"]["adapter_mode"] == "public_search_list_detail"
    assert sources["中国政府采购网"]["login_mode"] == "not_required"
    assert sources["中国政府采购网"]["active_rule_version_id"] is not None
    assert sources["建设网"]["login_mode"] == "login_required"


def test_protected_sources_api_requires_authentication(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.get("/api/sources")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"

