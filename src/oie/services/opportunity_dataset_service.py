from __future__ import annotations

import sqlite3
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class OpportunityDatasetService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.db_path = self.ctx.config.get("database", {}).get("path", "data/oie.db")

    def build_dataset(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        try:
            rows = conn.execute(
                """
                SELECT
                    c.company_key,
                    c.company_display,
                    c.company_normalized,
                    c.resolved_domain,
                    COALESCE(MAX(j.title), '') AS sample_job_title,
                    COUNT(DISTINCT j.job_key) AS jobs_count,
                    COALESCE(MAX(l.contact_name), '') AS contact_name,
                    COALESCE(MAX(l.contact_title), '') AS contact_title,
                    COALESCE(MAX(l.email), '') AS email,
                    COALESCE(MAX(l.linkedin_url), '') AS linkedin_url
                FROM companies c
                LEFT JOIN jobs j
                    ON j.company_key = c.company_key
                LEFT JOIN leads l
                    ON l.company_key = c.company_key
                GROUP BY
                    c.company_key,
                    c.company_display,
                    c.company_normalized,
                    c.resolved_domain
                ORDER BY jobs_count DESC, c.company_display ASC
                """
            ).fetchall()
        finally:
            conn.close()

        dataset = [dict(row) for row in rows]
        self.ctx.metrics["opportunity_dataset_rows"] = len(dataset)
        return dataset

    def build_top_opportunities(self, limit: int = 25) -> List[Dict[str, Any]]:
        dataset = self.build_dataset()
        return dataset[:limit]
