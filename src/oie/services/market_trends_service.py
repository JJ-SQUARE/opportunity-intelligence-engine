from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.persistence.context import PersistenceContext
from oie.persistence.repository_provider import RepositoryProvider


class MarketTrendsService:
    def __init__(
        self,
        ctx: RunContext,
        repositories: RepositoryProvider | None = None,
    ) -> None:
        self.ctx = ctx
        self.persistence = PersistenceContext.from_run_context(ctx)
        self.repositories = repositories or RepositoryProvider.from_persistence(self.persistence)
        self.job_repository = self.repositories.job_repository

    def build_source_trends(self) -> List[Dict[str, Any]]:
        result = self.job_repository.list_source_trends()
        self.ctx.metrics["market_trends_sources_rows"] = len(result)
        return result

    def build_country_trends(self) -> List[Dict[str, Any]]:
        result = self.job_repository.list_location_trends()
        self.ctx.metrics["market_trends_country_rows"] = len(result)
        return result

    def build_new_companies_by_source(self) -> List[Dict[str, Any]]:
        result = self.job_repository.list_new_companies_by_source()
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
