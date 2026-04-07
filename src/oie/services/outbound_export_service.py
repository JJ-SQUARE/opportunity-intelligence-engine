from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


COMMERCIAL_PIPELINE_FIELDS = [
    "company_key",
    "company_display",
    "company_normalized",
    "resolved_domain",
    "domain_source",
    "domain_confidence",
    "domain_candidate",
    "domain_validation_status",
    "domain_review_required",
    "domain_ai_decision",
    "company_type_ai",
    "classification_confidence_ai",
    "industry",
    "employee_range",
    "company_size",
    "linkedin_company_url",
    "company_description",
    "opportunity_score",
    "score_openings",
    "score_remote",
    "score_contractor",
    "score_multi_source",
    "score_company_type",
    "best_contact_name",
    "best_contact_title",
    "best_contact_email",
    "best_contact_linkedin_url",
    "best_lead_source",
    "best_lead_confidence",
    "best_lead_relevance_score",
    "best_email_quality_score",
    "best_lead_capture_reason",
]


APOLLO_IMPORT_FIELDS = [
    "name",
    "website",
    "linkedin_url",
]


class OutboundExportService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.db_path = self.ctx.paths.get("db_path") or self.ctx.config.get("database", {}).get("path", "data/oie.db")

    def _output_dir(self) -> Path:
        output_dir = Path(
            self.ctx.paths.get("output_dir")
            or Path(self.ctx.config.get("outputs", {}).get("path", "data/outputs")) / self.ctx.run_id
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        self.ctx.paths["output_dir"] = str(output_dir)
        return output_dir

    def _query_rows(self, query: str, params: tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def _write_csv(self, path: Path, fieldnames: List[str], rows: List[Dict[str, Any]]) -> str:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fieldnames})
        return str(path)

    def _build_commercial_pipeline_rows(self) -> List[Dict[str, Any]]:
        query = """
        WITH ranked_leads AS (
            SELECT
                l.company_key,
                l.contact_name,
                l.contact_title,
                l.email,
                l.linkedin_url,
                l.lead_source,
                l.lead_confidence,
                COALESCE(l.email_quality_score, 0) AS email_quality_score,
                COALESCE(l.lead_capture_reason, '') AS lead_capture_reason,
                COALESCE(l.lead_relevance_score, 0) AS lead_relevance_score,
                ROW_NUMBER() OVER (
                    PARTITION BY l.company_key
                    ORDER BY
                        COALESCE(l.lead_relevance_score, 0) DESC,
                        COALESCE(l.email_quality_score, 0) DESC,
                        COALESCE(l.lead_confidence, 0) DESC,
                        CASE LOWER(COALESCE(l.lead_source, ''))
                            WHEN 'apollo_people' THEN 3
                            WHEN 'hunter_domain_search' THEN 2
                            WHEN 'stub_generation' THEN 1
                            ELSE 0
                        END DESC,
                        CASE WHEN COALESCE(l.linkedin_url, '') <> '' THEN 1 ELSE 0 END DESC,
                        COALESCE(l.contact_name, '') ASC
                ) AS rn
            FROM leads l
            WHERE l.run_id = ?
        ),
        best_leads AS (
            SELECT
                company_key,
                contact_name AS best_contact_name,
                contact_title AS best_contact_title,
                email AS best_contact_email,
                linkedin_url AS best_contact_linkedin_url,
                lead_source AS best_lead_source,
                lead_confidence AS best_lead_confidence,
                lead_relevance_score AS best_lead_relevance_score,
                email_quality_score AS best_email_quality_score,
                lead_capture_reason AS best_lead_capture_reason
            FROM ranked_leads
            WHERE rn = 1
        ),
        run_scores AS (
            SELECT
                cs.company_key,
                cs.opportunity_score,
                cs.score_openings,
                cs.score_remote,
                cs.score_contractor,
                cs.score_multi_source,
                cs.score_company_type
            FROM company_scores cs
            WHERE cs.run_id = ?
        )
        SELECT
            c.company_key,
            c.company_display,
            c.company_normalized,
            COALESCE(c.resolved_domain, '') AS resolved_domain,
            COALESCE(c.domain_source, '') AS domain_source,
            COALESCE(c.domain_confidence, 0) AS domain_confidence,
            COALESCE(c.domain_candidate, '') AS domain_candidate,
            COALESCE(c.domain_validation_status, '') AS domain_validation_status,
            COALESCE(c.domain_review_required, 0) AS domain_review_required,
            COALESCE(c.domain_ai_decision, '') AS domain_ai_decision,
            COALESCE(c.company_type_ai, '') AS company_type_ai,
            COALESCE(c.classification_confidence_ai, 0) AS classification_confidence_ai,
            COALESCE(c.industry, '') AS industry,
            COALESCE(c.employee_range, '') AS employee_range,
            COALESCE(c.company_size, '') AS company_size,
            COALESCE(c.linkedin_company_url, '') AS linkedin_company_url,
            COALESCE(c.company_description, '') AS company_description,
            COALESCE(s.opportunity_score, 0) AS opportunity_score,
            COALESCE(s.score_openings, 0) AS score_openings,
            COALESCE(s.score_remote, 0) AS score_remote,
            COALESCE(s.score_contractor, 0) AS score_contractor,
            COALESCE(s.score_multi_source, 0) AS score_multi_source,
            COALESCE(s.score_company_type, 0) AS score_company_type,
            COALESCE(bl.best_contact_name, '') AS best_contact_name,
            COALESCE(bl.best_contact_title, '') AS best_contact_title,
            COALESCE(bl.best_contact_email, '') AS best_contact_email,
            COALESCE(bl.best_contact_linkedin_url, '') AS best_contact_linkedin_url,
            COALESCE(bl.best_lead_source, '') AS best_lead_source,
            COALESCE(bl.best_lead_confidence, 0) AS best_lead_confidence,
            COALESCE(bl.best_lead_relevance_score, 0) AS best_lead_relevance_score,
            COALESCE(bl.best_email_quality_score, 0) AS best_email_quality_score,
            COALESCE(bl.best_lead_capture_reason, '') AS best_lead_capture_reason
        FROM run_scores s
        INNER JOIN companies c
            ON c.company_key = s.company_key
        LEFT JOIN best_leads bl
            ON bl.company_key = c.company_key
        ORDER BY
            COALESCE(s.opportunity_score, 0) DESC,
            CASE WHEN COALESCE(c.domain_validation_status, '') = 'accepted' THEN 1 ELSE 0 END DESC,
            CASE WHEN COALESCE(bl.best_contact_email, '') <> '' THEN 1 ELSE 0 END DESC,
            c.company_display ASC
        """
        return self._query_rows(query, (self.ctx.run_id, self.ctx.run_id))

    def export_commercial_pipeline(self) -> str:
        rows = self._build_commercial_pipeline_rows()
        path = self._output_dir() / "commercial_pipeline.csv"
        output = self._write_csv(path, COMMERCIAL_PIPELINE_FIELDS, rows)
        self.ctx.paths["commercial_pipeline_csv"] = output
        self.ctx.metrics["commercial_pipeline_rows"] = len(rows)
        return output

    def export_apollo_import(self) -> str:
        rows = self._build_commercial_pipeline_rows()
        apollo_rows = []

        seen = set()
        for row in rows:
            website = (row.get("resolved_domain") or "").strip()
            if not website:
                continue

            key = website.lower()
            if key in seen:
                continue
            seen.add(key)

            apollo_rows.append(
                {
                    "name": row.get("company_display", ""),
                    "website": website,
                    "linkedin_url": row.get("linkedin_company_url", ""),
                }
            )

        path = self._output_dir() / "apollo_import.csv"
        output = self._write_csv(path, APOLLO_IMPORT_FIELDS, apollo_rows)
        self.ctx.paths["apollo_import_csv"] = output
        self.ctx.metrics["apollo_import_rows"] = len(apollo_rows)
        return output

    def export_all(self) -> None:
        self.export_commercial_pipeline()
        self.export_apollo_import()
