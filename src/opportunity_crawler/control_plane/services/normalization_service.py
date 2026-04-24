from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib
import json
import sqlite3

from opportunity_crawler.control_plane.services.ai_analysis_service import AIAnalysisService
from opportunity_crawler.control_plane.services.dedupe_service import DedupeService
from opportunity_crawler.control_plane.services.scoring_service import ScoringService
from opportunity_crawler.shared.db.base import connect_sqlite


@dataclass(frozen=True)
class ManualCandidateInput:
    source_id: int
    title: str
    body: str
    url: str | None = None
    organization_name: str | None = None
    region: str | None = None
    industry: str | None = None
    project_stage: str | None = None
    budget_amount: float | None = None


class CandidateCreationService:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.dedupe = DedupeService()
        self.scoring = ScoringService()
        self.ai = AIAnalysisService(provider_enabled=False)

    def create_from_manual_import(self, payload: ManualCandidateInput) -> dict[str, Any]:
        with connect_sqlite(self.database_path) as connection:
            source = connection.execute(
                "SELECT priority FROM sources WHERE id = ?",
                (payload.source_id,),
            ).fetchone()
            if source is None:
                raise KeyError("source_not_found")

            fingerprint = hashlib.sha256(payload.body.encode("utf-8")).hexdigest()
            source_item_key = payload.url or fingerprint
            dedupe_key = self.dedupe.build_dedupe_key(
                source_id=payload.source_id,
                source_item_key=source_item_key,
                url=payload.url,
                title=payload.title,
                organization_name=payload.organization_name,
                published_at=None,
                content_fingerprint=fingerprint,
            )
            existing = connection.execute(
                "SELECT * FROM opportunity_candidates WHERE dedupe_key = ?",
                (dedupe_key,),
            ).fetchone()
            if existing is not None:
                return dict(existing)

            connection.execute(
                """
                INSERT INTO raw_evidence_items (
                    source_id, source_item_key, url, title, raw_text, content_fingerprint
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (payload.source_id, source_item_key, payload.url, payload.title, payload.body, fingerprint),
            )
            evidence_id = int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])
            candidate_data = {
                "title": payload.title,
                "organization_name": payload.organization_name,
                "region": payload.region,
                "industry": payload.industry,
                "project_stage": payload.project_stage,
                "budget_amount": payload.budget_amount,
                "raw_text": payload.body,
                "source_priority": source["priority"],
            }
            scoring = self.scoring.score_candidate(candidate_data)
            connection.execute(
                """
                INSERT INTO opportunity_candidates (
                    source_id, evidence_id, dedupe_key, title, organization_name,
                    region, industry, project_stage, budget_amount, score, priority_label
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.source_id,
                    evidence_id,
                    dedupe_key,
                    payload.title,
                    payload.organization_name,
                    payload.region,
                    payload.industry,
                    payload.project_stage,
                    payload.budget_amount,
                    scoring.score,
                    scoring.priority_label,
                ),
            )
            candidate_id = int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])
            analysis = self.ai.analyze(candidate_data)
            connection.execute(
                """
                INSERT INTO candidate_analysis (
                    candidate_id, extracted_facts_json, inferred_analysis_json,
                    scoring_reasons_json, outreach_json, provider_metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id,
                    _json(analysis.extracted_facts),
                    _json(analysis.inferred_analysis),
                    _json(scoring.reasons),
                    _json(analysis.outreach),
                    _json(analysis.provider_metadata),
                ),
            )
            self._ensure_customer(connection, payload.organization_name, payload.region, payload.industry)
            connection.commit()
            row = connection.execute(
                "SELECT * FROM opportunity_candidates WHERE id = ?",
                (candidate_id,),
            ).fetchone()
        return dict(row)

    def _ensure_customer(
        self,
        connection: sqlite3.Connection,
        organization_name: str | None,
        region: str | None,
        industry: str | None,
    ) -> None:
        if not organization_name:
            return
        connection.execute(
            """
            INSERT OR IGNORE INTO customers (name, region, industry, source)
            VALUES (?, ?, ?, 'opportunity')
            """,
            (organization_name, region, industry),
        )


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)

