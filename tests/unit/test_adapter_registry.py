from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.collection.adapters.registry import AdapterRegistry


def test_adapter_registry_resolves_planned_modes() -> None:
    registry = AdapterRegistry.default()

    assert registry.resolve("public_search_list_detail").mode == "public_search_list_detail"
    assert registry.resolve("manual_import").mode == "manual_import"
    assert registry.resolve("api_or_feed").mode == "api_or_feed"


def test_adapter_registry_rejects_unsupported_mode() -> None:
    registry = AdapterRegistry.default()

    try:
        registry.resolve("custom_script")
    except KeyError as exc:
        assert "custom_script" in str(exc)
    else:
        raise AssertionError("expected KeyError")

