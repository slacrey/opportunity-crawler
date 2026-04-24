from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.collection.rules.loader import load_collection_rules
from opportunity_crawler.shared.db.base import apply_migrations, connect_sqlite


def test_rule_loader_returns_basic_and_active_advanced_rules(tmp_path: Path) -> None:
    connection = connect_sqlite(tmp_path / "opportunity.db")
    apply_migrations(connection)

    try:
        source_id = connection.execute("SELECT id FROM sources WHERE name = '中国政府采购网'").fetchone()[0]
        rules = load_collection_rules(connection, source_id=source_id)

        assert "昆山" in rules.basic["regions"]
        assert rules.basic["frequency"] == "daily"
        assert rules.advanced["adapter_mode"] == "public_search_list_detail"
        assert rules.advanced["version"] == 1
    finally:
        connection.close()

