from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CRMImportResult:
    imported: list[dict[str, Any]]
    duplicates: list[dict[str, Any]]
    errors: list[dict[str, Any]]


class CRMImportService:
    def __init__(self, *, existing_customer_names: set[str] | None = None) -> None:
        self.existing_customer_names = existing_customer_names or set()

    def import_rows(self, rows: list[dict[str, Any]]) -> CRMImportResult:
        imported: list[dict[str, Any]] = []
        duplicates: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for index, row in enumerate(rows, start=1):
            name = str(row.get("name") or "").strip()
            if not name:
                errors.append({"row": index, "field": "name", "message": "customer name is required"})
                continue
            if name in self.existing_customer_names:
                duplicates.append({"row": index, "name": name})
                continue
            imported.append({"name": name, **{key: value for key, value in row.items() if key != "name"}})
        return CRMImportResult(imported=imported, duplicates=duplicates, errors=errors)

