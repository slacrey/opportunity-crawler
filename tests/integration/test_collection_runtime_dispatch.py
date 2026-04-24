from __future__ import annotations

import sys
from pathlib import Path
import asyncio

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.agent.runtime.collection_runner import CollectionRunner
from opportunity_crawler.shared.contracts.agent_protocol import CollectionEventKind, CollectionCommandMessage


def test_collection_runner_returns_trial_run_preview_without_persistence() -> None:
    asyncio.run(_assert_collection_runner_returns_trial_run_preview_without_persistence())


async def _assert_collection_runner_returns_trial_run_preview_without_persistence() -> None:
    runner = CollectionRunner()
    command = CollectionCommandMessage(
        message_type="collection_command",
        command="trial_run_advanced_rule",
        command_id="cmd-1",
        run_id="trial-1",
        source_id=10,
        rule_version=2,
        adapter_mode="manual_import",
        login_mode="not_required",
        draft_rule_payload={"adapter_mode": "manual_import"},
        max_items=1,
    )

    result = await runner.trial_run_advanced_rule(command)

    assert result["event_kind"] is CollectionEventKind.TRIAL_RUN_COMPLETED
    assert result["rows"] == []
    assert result["diagnostic_snapshot"]["trial_run"] is True
