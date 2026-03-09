from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.services.collection_service import CollectionService
from oie.services.company_identity_service import CompanyIdentityService
from oie.services.domain_resolution_service import DomainResolutionService
from oie.services.hiring_signals_service import HiringSignalsService
from oie.services.job_dedup_service import JobDedupService
from oie.services.normalization_service import NormalizationService
from oie.services.opportunity_scoring_service import OpportunityScoringService
from oie.services.persistence_service import PersistenceService
from oie.services.provider_control_service import ProviderControlService


class PipelineOrchestrator:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.collection_service = CollectionService(ctx)
        self.normalization_service = NormalizationService(ctx)
        self.job_dedup_service = JobDedupService(ctx)
        self.hiring_signals_service = HiringSignalsService(ctx)
        self.company_identity_service = CompanyIdentityService(ctx)
        self.domain_resolution_service = DomainResolutionService(ctx)
        self.opportunity_scoring_service = OpportunityScoringService(ctx)
        self.persistence_service = PersistenceService(ctx)
        self.provider_control_service = ProviderControlService(ctx)

    def run_initial_stages(self) -> List[Dict[str, Any]]:
        jobs = self.collection_service.collect()
        jobs = self.normalization_service.normalize(jobs)
        jobs = self.job_dedup_service.dedupe(jobs)
        return jobs

    def run_company_pipeline(self) -> List[Dict[str, Any]]:
        jobs = self.run_initial_stages()
        companies = self.hiring_signals_service.aggregate_by_company(jobs)
        companies = self.company_identity_service.enrich_company_identity(companies)
        companies = self.domain_resolution_service.resolve_domains(companies)
        companies = self.opportunity_scoring_service.score_companies(companies)
        return companies

    def run(self) -> Dict[str, Any]:
        self.provider_control_service.initialize()
        self.provider_control_service.sync_budget_metrics()

        companies = self.run_company_pipeline()
        status = "company_pipeline_completed"

        self.persistence_service.persist_run_snapshot(status=status)

        return {
            "run_id": self.ctx.run_id,
            "run_date": self.ctx.run_date,
            "status": status,
            "companies_count": len(companies),
            "top_companies": companies[:5],
            "metrics": self.ctx.metrics,
            "budgets": self.ctx.budgets,
            "db_path": self.ctx.paths.get("db_path"),
        }
