from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_control_panel_core_workflow_files_exist() -> None:
    expected = [
        ROOT / "frontend/src/pages/DashboardPage.vue",
        ROOT / "frontend/src/pages/SourcesPage.vue",
        ROOT / "frontend/src/pages/ReviewQueuePage.vue",
        ROOT / "frontend/src/pages/OpportunityDetailPage.vue",
        ROOT / "frontend/src/components/AdvancedRuleEditor.vue",
        ROOT / "frontend/src/styles/theme.css",
    ]

    assert all(path.exists() for path in expected)


def test_control_panel_uses_json_api_and_management_layout() -> None:
    layout = (ROOT / "frontend/src/layouts/AdminLayout.vue").read_text(encoding="utf-8")
    client = (ROOT / "frontend/src/api/client.ts").read_text(encoding="utf-8")

    assert "/api/" in client
    assert "admin-shell" in layout
    assert "admin-sidebar" in layout
