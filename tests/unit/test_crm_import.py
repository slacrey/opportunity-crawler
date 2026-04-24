from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.integrations.crm import CRMImportService


def test_crm_import_reports_row_errors_and_duplicate_customers() -> None:
    result = CRMImportService(existing_customer_names={"昆山某单位"}).import_rows(
        [
            {"name": "昆山某单位", "region": "昆山"},
            {"region": "太仓"},
            {"name": "太仓某单位", "region": "太仓"},
        ]
    )

    assert result.imported == [{"name": "太仓某单位", "region": "太仓"}]
    assert result.errors == [{"row": 2, "field": "name", "message": "customer name is required"}]
    assert result.duplicates == [{"row": 1, "name": "昆山某单位"}]

