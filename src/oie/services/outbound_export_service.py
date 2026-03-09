from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Dict, List

from oie.orchestration.run_context import RunContext


class OutboundExportService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.db_path = self.ctx.config.get("database", {}).get("path", "data/oie.db")
        self.output_dir = Path(
            self.ctx.config.get("outputs", {}).get("path", "data/outputs")
        ) / self.ctx.run_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _write_csv(self, filename: str, rows: List[Dict[str, object]]) -> str:
        output_path = self.output_dir / filename
        fieldnames = list(rows[0].keys()) if rows else []

        with output_path.open("w", encoding="utf-8", newline="") as fh:
            if fieldnames:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            else:
                fh.write("")

        return str(output_path)

    def _load_dataset(self, company_types: List[str] | None = None) -> List[Dict[str, object]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            sql = """
                SELECT
                    c.company_key,
                    c.company_display,
                    c.resolved_domain,
                    c.industry,
                    c.employee_range,
                    c.linkedin_company_url,
                    c.company_description,
                    c.company_type_ai,
                    c.classification_confidence_ai,
                    COALESCE(MAX(cs.opportunity_score), 0) AS opportunity_score,
                    COALESCE(MAX(l.contact_name), '') AS contact_name,
                    COALESCE(MAX(l.contact_title), '') AS contact_title,
                    COALESCE(MAX(l.email), '') AS email,
                    COALESCE(MAX(l.linkedin_url), '') AS linkedin_url,
                    COALESCE(MAX(l.lead_source), '') AS lead_source,
                    COALESCE(MAX(l.lead_confidence), 0) AS lead_confidence,
                    COALESCE(MAX(j.title), '') AS sample_job_title
                FROM companies c
                LEFT JOIN company_scores cs
                    ON cs.company_key = c.company_key
                LEFT JOIN leads l
                    ON l.company_key = c.company_key
                LEFT JOIN jobs j
                    ON j.company_key = c.company_key
            """
            params: tuple = ()

            if company_types:
                placeholders = ",".join("?" for _ in company_types)
                sql += f" WHERE c.company_type_ai IN ({placeholders}) "
                params = tuple(company_types)

            sql += """
                GROUP BY
                    c.company_key,
                    c.company_display,
                    c.resolved_domain,
                    c.industry,
                    c.employee_range,
                    c.linkedin_company_url,
                    c.company_description,
                    c.company_type_ai,
                    c.classification_confidence_ai
                ORDER BY opportunity_score DESC, c.company_display ASC
            """

            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()

        return [dict(row) for row in rows]

    def export_top_opportunities(self, limit: int = 50) -> str:
        rows = self._load_dataset()[:limit]
        path = self._write_csv("top_opportunities.csv", rows)
        self.ctx.paths["top_opportunities_csv"] = path
        return path

    def export_company_segment(self, segment_name: str, company_types: List[str]) -> str:
        rows = self._load_dataset(company_types=company_types)
        path = self._write_csv(f"{segment_name}.csv", rows)
        self.ctx.paths[f"{segment_name}_csv"] = path
        return path

    def export_apollo_import(self) -> str:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT
                    c.company_display AS account_name,
                    c.resolved_domain AS website,
                    c.linkedin_company_url AS company_linkedin_url,
                    c.industry AS industry,
                    c.company_description AS company_description,
                    l.contact_name AS first_name,
                    l.contact_title AS title,
                    l.email AS email,
                    l.linkedin_url AS person_linkedin_url
                FROM companies c
                LEFT JOIN leads l
                    ON l.company_key = c.company_key
                WHERE COALESCE(l.email, '') != ''
                ORDER BY c.company_display ASC
                """
            ).fetchall()
        finally:
            conn.close()

        path = self._write_csv("apollo_import.csv", [dict(row) for row in rows])
        self.ctx.paths["apollo_import_csv"] = path
        return path

    def export_all(self) -> None:
        self.export_top_opportunities()
        self.export_company_segment("end_clients", ["end_client"])
        self.export_company_segment("vendors", ["staffing", "consulting"])
        self.export_company_segment("marketplaces", ["marketplace"])
        self.export_apollo_import()
