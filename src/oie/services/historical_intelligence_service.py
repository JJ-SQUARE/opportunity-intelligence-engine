from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.persistence.context import PersistenceContext
from oie.persistence.repository_provider import RepositoryProvider


class HistoricalIntelligenceService:
    def __init__(
        self,
        ctx: RunContext,
        repositories: RepositoryProvider | None = None,
    ) -> None:
        self.ctx = ctx
        self.persistence = PersistenceContext.from_run_context(ctx)
        self.repositories = repositories or RepositoryProvider.from_persistence(self.persistence)
        self.job_repository = self.repositories.job_repository

    def build_company_hiring_history(self) -> List[Dict[str, Any]]:
        history = self.job_repository.list_company_hiring_history()
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
