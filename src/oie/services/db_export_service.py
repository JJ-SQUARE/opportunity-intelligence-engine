from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import List

from oie.orchestration.run_context import RunContext


class DBExportService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.db_path = self.ctx.config.get("database", {}).get("path", "data/oie.db")
        self.output_dir = Path(
            self.ctx.config.get("outputs", {}).get("path", "data/outputs")
        ) / self.ctx.run_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _export_query_to_csv(self, sql: str, output_name: str, params: tuple = ()) -> str:
        output_path = self.output_dir / output_name

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
                company_key,
                company_display,
                company_normalized,
                resolved_domain,
                domain_source,
                domain_confidence
            FROM companies
            ORDER BY company_display
            """,
            "companies_export.csv",
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
