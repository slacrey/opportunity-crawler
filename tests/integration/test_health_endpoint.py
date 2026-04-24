from __future__ import annotations

from pathlib import Path

from tests.integration.api_helpers import build_client


def test_health_endpoint_reports_database_and_runtime_readiness(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["database"]["ok"] is True
    assert payload["migrations"]["ok"] is True
    assert payload["browser"]["ok"] is False
    assert payload["browser"]["detail"] == "no Agent online and no trial browser runtime configured"
    assert "secrets" not in payload


def test_health_endpoint_reports_configured_trial_browser_runtime(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    client.app.state.trial_browser_runtime = FakeBrowserRuntime()

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["browser"] == {
        "ok": True,
        "detail": "trial browser runtime configured",
    }


class FakeBrowserRuntime:
    def fetch_html(self, url: str) -> str:
        return url
