from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import List

from oie.orchestration.run_context import RunContext


class DBExportService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.db_path = self.ctx.paths.get("db_path") or self.ctx.config.get("database", {}).get("path", "data/oie.db")

    def _get_output_dir(self) -> Path:
        output_dir_value = self.ctx.paths.get("output_dir")
        if not output_dir_value:
            base_output = ((self.ctx.config or {}).get("outputs", {}) or {}).get("path") or "data/outputs"
            run_id = self.ctx.run_id or "manual_run"
            output_dir_value = str(Path(base_output) / run_id)
            self.ctx.paths["output_dir"] = output_dir_value

        output_dir = Path(output_dir_value)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _export_query_to_csv(self, sql: str, output_name: str, params: tuple = ()) -> str:
        output_dir = self._get_output_dir()
        output_path = output_dir / output_name

        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()

        fieldnames: List[str] = list(rows[0].keys()) if rows else []

        with output_path.open("w", encoding="utf-8", newline="") as fh:
            if fieldnames:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows([dict(row) for row in rows])
            else:
                fh.write("")

        return str(output_path)

    def export_run_companies(self) -> str:
        path = self._export_query_to_csv(
            """
            SELECT
                c.company_key,
                c.company_display,
                c.company_normalized,
                c.resolved_domain,
                c.domain_source,
                c.domain_confidence,
                c.domain_candidate,
                c.domain_validation_status,
                c.domain_review_required,
                c.domain_ai_decision,
                c.industry,
                c.employee_range,
                c.company_size,
                c.linkedin_company_url,
                c.company_description,
                c.company_type_ai,
                c.classification_confidence_ai
            FROM companies c
            INNER JOIN (
                SELECT DISTINCT company_key
                FROM company_scores
                WHERE run_id = ?
                  AND company_key IS NOT NULL
                  AND company_key <> ''
            ) rs
                ON rs.company_key = c.company_key
            ORDER BY c.company_display, c.company_key
            """,
            "companies_export.csv",
            (self.ctx.run_id,),
        )
        self.ctx.paths["companies_export"] = path
        return path

    def export_run_jobs(self) -> str:
        path = self._export_query_to_csv(
            """
            SELECT
                job_key,
                run_id,
                run_date,
                title,
                company,
                company_key,
                location,
                job_url,
                apply_url,
                source,
                detected_at
            FROM jobs
            WHERE run_id = ?
            ORDER BY title
            """,
            "jobs_export.csv",
            (self.ctx.run_id,),
        )
        self.ctx.paths["jobs_export"] = path
        return path

    def export_run_leads(self) -> str:
        path = self._export_query_to_csv(
            """
            SELECT
                lead_key,
                run_id,
                run_date,
                company_key,
                contact_name,
                contact_title,
                email,
                linkedin_url
            FROM leads
            WHERE run_id = ?
            ORDER BY contact_name
            """,
            "leads_export.csv",
            (self.ctx.run_id,),
        )
        self.ctx.paths["leads_export"] = path
        return path

    def export_all(self) -> None:
        self.export_run_companies()
        self.export_run_jobs()
        self.export_run_leads()
