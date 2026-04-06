from __future__ import annotations

import sqlite3
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class HistoricalIntelligenceService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.db_path = (
            self.ctx.paths.get("db_path")
            or self.ctx.config.get("database", {}).get("path", "data/oie.db")
        )

    def build_company_hiring_history(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT
                    c.company_key,
                    c.company_display,
                    c.resolved_domain,
                    j.run_id,
                    j.run_date,
                    COUNT(DISTINCT j.job_key) AS openings
                FROM companies c
                JOIN jobs j
                    ON j.company_key = c.company_key
                GROUP BY
                    c.company_key,
                    c.company_display,
                    c.resolved_domain,
                    j.run_id,
                    j.run_date
                ORDER BY
                    c.company_display ASC,
                    j.run_date ASC,
                    j.run_id ASC
                """
            ).fetchall()
        finally:
            conn.close()

        history = [dict(row) for row in rows]
        self.ctx.metrics["historical_company_rows"] = len(history)
        return history

    def build_company_growth_summary(self) -> List[Dict[str, Any]]:
        history = self.build_company_hiring_history()

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for row in history:
            grouped.setdefault(row["company_key"], []).append(row)

        summary: List[Dict[str, Any]] = []

        for company_key, rows in grouped.items():
            ordered = sorted(
                rows,
                key=lambda x: (x["run_date"], x["run_id"]),
            )
            first = ordered[0]
            last = ordered[-1]

            first_openings = int(first["openings"] or 0)
            last_openings = int(last["openings"] or 0)
            growth = last_openings - first_openings

            if growth > 0:
                trend = "growing"
            elif growth < 0:
                trend = "declining"
            else:
                trend = "stable"

            summary.append(
                {
                    "company_key": company_key,
                    "company_display": last["company_display"],
                    "resolved_domain": last["resolved_domain"],
                    "first_run_id": first["run_id"],
                    "last_run_id": last["run_id"],
                    "first_run_date": first["run_date"],
                    "last_run_date": last["run_date"],
                    "first_openings": first_openings,
                    "last_openings": last_openings,
                    "openings_growth": growth,
                    "trend": trend,
                    "runs_observed": len(ordered),
                }
            )

        summary.sort(
            key=lambda x: (x["openings_growth"], x["last_openings"]),
            reverse=True,
        )

        self.ctx.metrics["historical_growth_companies"] = len(summary)
        return summary
