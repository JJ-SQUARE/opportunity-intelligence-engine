from __future__ import annotations

import sqlite3
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class MarketTrendsService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.db_path = self.ctx.paths.get("db_path") or self.ctx.config.get("database", {}).get("path", "data/oie.db")

    def build_source_trends(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT
                    source,
                    COUNT(DISTINCT job_key) AS jobs_count,
                    COUNT(DISTINCT company_key) AS companies_count,
                    COUNT(DISTINCT run_id) AS runs_count
                FROM jobs
                GROUP BY source
                ORDER BY jobs_count DESC, companies_count DESC, source ASC
                """
            ).fetchall()
        finally:
            conn.close()

        result = [dict(row) for row in rows]
        self.ctx.metrics["market_trends_sources_rows"] = len(result)
        return result

    def build_country_trends(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT
                    location,
                    COUNT(DISTINCT job_key) AS jobs_count,
                    COUNT(DISTINCT company_key) AS companies_count
                FROM jobs
                WHERE COALESCE(location, '') != ''
                GROUP BY location
                ORDER BY jobs_count DESC, companies_count DESC, location ASC
                """
            ).fetchall()
        finally:
            conn.close()

        result = [dict(row) for row in rows]
        self.ctx.metrics["market_trends_country_rows"] = len(result)
        return result

    def build_new_companies_by_source(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                WITH company_first_source AS (
                    SELECT
                        j.company_key,
                        MIN(j.run_date) AS first_run_date
                    FROM jobs j
                    WHERE j.company_key IS NOT NULL
                    GROUP BY j.company_key
                ),
                company_first_source_detail AS (
                    SELECT
                        j.company_key,
                        j.source,
                        j.run_date
                    FROM jobs j
                    JOIN company_first_source cfs
                      ON cfs.company_key = j.company_key
                     AND cfs.first_run_date = j.run_date
                )
                SELECT
                    source,
                    COUNT(DISTINCT company_key) AS new_companies_count
                FROM company_first_source_detail
                GROUP BY source
                ORDER BY new_companies_count DESC, source ASC
                """
            ).fetchall()
        finally:
            conn.close()

        result = [dict(row) for row in rows]
        self.ctx.metrics["market_trends_new_companies_rows"] = len(result)
        return result

    def build_summary(self) -> Dict[str, Any]:
        sources = self.build_source_trends()
        countries = self.build_country_trends()
        new_companies = self.build_new_companies_by_source()

        summary = {
            "run_id": self.ctx.run_id,
            "run_date": self.ctx.run_date,
            "top_sources": sources[:10],
            "top_locations": countries[:10],
            "top_new_company_sources": new_companies[:10],
            "totals": {
                "sources": len(sources),
                "locations": len(countries),
                "new_company_sources": len(new_companies),
            },
        }

        self.ctx.metrics["market_trends_summary_generated"] = True
        return summary
