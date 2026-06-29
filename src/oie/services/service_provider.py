from __future__ import annotations

from dataclasses import dataclass

from oie.orchestration.run_context import RunContext
from oie.persistence.context import PersistenceContext
from oie.persistence.repository_provider import RepositoryProvider
from oie.services.company_identity_service import CompanyIdentityService
from oie.services.db_export_service import DBExportService
from oie.services.executive_summary_service import ExecutiveSummaryService
from oie.services.historical_intelligence_service import HistoricalIntelligenceService
from oie.services.market_trends_service import MarketTrendsService
from oie.services.master_dedup_service import MasterDedupService
from oie.services.opportunity_dataset_service import OpportunityDatasetService
from oie.services.outbound_export_service import OutboundExportService
from oie.services.persistence_service import PersistenceService
from oie.services.provider_control_service import ProviderControlService
from oie.services.run_readiness_service import RunReadinessService


@dataclass(frozen=True)
class ServiceProvider:
    ctx: RunContext
    persistence_service: PersistenceService
    persistence: PersistenceContext
    repositories: RepositoryProvider
    provider_control_service: ProviderControlService
    db_export_service: DBExportService
    outbound_export_service: OutboundExportService
    executive_summary_service: ExecutiveSummaryService
    run_readiness_service: RunReadinessService
    company_identity_service: CompanyIdentityService
    master_dedup_service: MasterDedupService
    opportunity_dataset_service: OpportunityDatasetService
    historical_intelligence_service: HistoricalIntelligenceService
    market_trends_service: MarketTrendsService

    @classmethod
    def from_run_context(cls, ctx: RunContext) -> "ServiceProvider":
        persistence_service = PersistenceService(ctx)
        provider_control_service = ProviderControlService(ctx)
        return cls(
            ctx=ctx,
            persistence_service=persistence_service,
            persistence=persistence_service.persistence,
            repositories=persistence_service.repositories,
            provider_control_service=provider_control_service,
            db_export_service=DBExportService(ctx, persistence=persistence_service.persistence),
            outbound_export_service=OutboundExportService(ctx, persistence=persistence_service.persistence),
            executive_summary_service=ExecutiveSummaryService(ctx, persistence=persistence_service.persistence),
            run_readiness_service=RunReadinessService(ctx, persistence=persistence_service.persistence),
            company_identity_service=CompanyIdentityService(ctx, repositories=persistence_service.repositories),
            master_dedup_service=MasterDedupService(ctx, repositories=persistence_service.repositories),
            opportunity_dataset_service=OpportunityDatasetService(ctx, repositories=persistence_service.repositories),
            historical_intelligence_service=HistoricalIntelligenceService(ctx, repositories=persistence_service.repositories),
            market_trends_service=MarketTrendsService(ctx, repositories=persistence_service.repositories),
        )
