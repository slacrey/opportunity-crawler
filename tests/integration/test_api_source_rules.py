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


def test_trial_run_rule_returns_adapter_preview_and_persists_snapshot(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    headers = auth_headers(client)
    source_id = first_source_id(client, headers)
    client.app.state.trial_browser_runtime = FakeBrowserRuntime(
        {
            "https://example.test/search": """
                <div class="item"><a href="/detail/1">昆山 AI 项目</a></div>
                <div class="item"><a href="/detail/2">太仓云平台</a></div>
            """,
            "https://example.test/detail/1": "<article class='content'>昆山 智慧城市 AI</article>",
            "https://example.test/detail/2": "<article class='content'>太仓 云平台 数字化</article>",
        }
    )

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
        },
    )
    version = create_response.json()["version"]

    trial_response = client.post(
        f"/api/sources/{source_id}/advanced-rules/{version}/trial-run",
        headers=headers,
        json={"max_items": 1},
    )

    assert trial_response.status_code == 200
    payload = trial_response.json()
    assert payload["preview_rows"] == [
        {
            "title": "昆山 AI 项目",
            "url": "https://example.test/detail/1",
            "raw_text": "昆山 智慧城市 AI",
            "source_item_key": "https://example.test/detail/1",
        }
    ]
    assert payload["diagnostic_snapshot"]["trial_run"] is True
    assert payload["diagnostic_snapshot"]["adapter_mode"] == "public_search_list_detail"

    versions_response = client.get(f"/api/sources/{source_id}/advanced-rules", headers=headers)
    created_version = next(rule for rule in versions_response.json()["items"] if rule["version"] == version)
    assert created_version["trial_run_snapshot"]["preview_rows"] == payload["preview_rows"]


class FakeBrowserRuntime:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages

    def fetch_html(self, url: str) -> str:
        return self.pages[url]
