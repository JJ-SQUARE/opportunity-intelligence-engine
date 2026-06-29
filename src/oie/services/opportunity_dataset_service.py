from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.persistence.context import PersistenceContext
from oie.persistence.company_repository import CompanyRepository
from oie.services.commercial_selection_service import CommercialSelectionService
from oie.services.commercial_signal_service import CommercialSignalService


class OpportunityDatasetService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.persistence = PersistenceContext.from_run_context(ctx)
        self.company_repository = CompanyRepository(persistence=self.persistence)
        self.commercial_signal_service = CommercialSignalService()
        self.commercial_selection_service = CommercialSelectionService(self.commercial_signal_service)

    def build_dataset(self) -> List[Dict[str, Any]]:
        rows = self.company_repository.list_opportunity_dataset_by_run(self.ctx.run_id)

        dataset = []
        for row in rows:
            record = dict(row)
            record = self.commercial_signal_service.finalize_row(record)
            dataset.append(record)

        dataset = self.commercial_selection_service.sort_companies_analytic(dataset)

        self.ctx.metrics["opportunity_dataset_rows"] = len(dataset)
        self.ctx.metrics["opportunity_dataset_reachability_ready"] = sum(
            1 for row in dataset if int(row.get("reachability_ready") or 0) == 1
        )
        self.ctx.metrics["opportunity_dataset_strong_icp"] = sum(
            1 for row in dataset if str(row.get("icp_bucket") or "") == "strong_icp"
        )
        return dataset

    def build_top_opportunities(self, limit: int = 25) -> List[Dict[str, Any]]:
        dataset = self.build_dataset()
        return self.commercial_selection_service.top_companies_analytic(dataset, limit=limit)
