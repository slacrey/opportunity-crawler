from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.shared.contracts.agent_protocol import (
    CollectionEventKind,
    CollectionEventMessage,
    ControlPlaneCommandKind,
    parse_agent_message,
    parse_control_plane_message,
)


def test_parse_start_collection_run_command() -> None:
    message = parse_control_plane_message(
        {
            "message_type": "collection_command",
            "command": "start_collection_run",
            "command_id": "cmd-1",
            "run_id": "run-1",
            "source_id": 10,
            "rule_version": 1,
            "adapter_mode": "public_search_list_detail",
            "login_mode": "not_required",
        }
    )

    assert message.command is ControlPlaneCommandKind.START_COLLECTION_RUN
    assert message.source_id == 10
    assert message.rule_version == 1


def test_collection_event_serializes_rows_and_diagnostic_snapshot() -> None:
    event = CollectionEventMessage(
        message_type="collection_event",
        event_kind=CollectionEventKind.RUN_SUCCEEDED,
        command_id="cmd-1",
        run_id="run-1",
        source_id=10,
        adapter_mode="public_search_list_detail",
        page_count=2,
        item_count=1,
        rows=[{"title": "商机", "url": "https://example.test"}],
        diagnostic_snapshot={"stop_reason": "max_pages_reached"},
    )

    payload = event.model_dump(mode="json")
    parsed = parse_agent_message(payload)

    assert parsed.event_kind is CollectionEventKind.RUN_SUCCEEDED
    assert parsed.rows == [{"title": "商机", "url": "https://example.test"}]
    assert parsed.diagnostic_snapshot["stop_reason"] == "max_pages_reached"

