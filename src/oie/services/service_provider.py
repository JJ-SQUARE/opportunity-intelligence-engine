from __future__ import annotations

from dataclasses import dataclass

from oie.orchestration.run_context import RunContext
from oie.persistence.context import PersistenceContext
from oie.persistence.repository_provider import RepositoryProvider
from oie.services.company_enrichment_service import CompanyEnrichmentService
from oie.services.company_identity_service import CompanyIdentityService
from oie.services.company_identity_ai_service import CompanyIdentityAIService
from oie.services.collection_service import CollectionService
from oie.services.collector_contribution_export_service import CollectorContributionExportService
from oie.services.collector_contribution_service import CollectorContributionService
from oie.services.collector_metrics_export_service import CollectorMetricsExportService
from oie.services.collector_metrics_service import CollectorMetricsService
from oie.services.collector_roi_export_service import CollectorROIExportService
from oie.services.collector_roi_service import CollectorROIService
from oie.services.commercial_selection_service import CommercialSelectionService
from oie.services.commercial_signal_service import CommercialSignalService
from oie.services.company_classification_service import CompanyClassificationService
from oie.services.db_export_service import DBExportService
from oie.services.domain_review_queue_service import DomainReviewQueueService
from oie.services.duplicate_report_service import DuplicateReportService
from oie.services.hiring_signals_service import HiringSignalsService
from oie.services.job_dedup_service import JobDedupService
from oie.services.domain_ai_validation_service import DomainAIValidationService
from oie.services.domain_resolution_service import DomainResolutionService
from oie.services.executive_summary_service import ExecutiveSummaryService
from oie.services.historical_export_service import HistoricalExportService
from oie.services.historical_intelligence_service import HistoricalIntelligenceService
from oie.services.job_intelligence_service import JobIntelligenceService
from oie.services.lead_generation_service import LeadGenerationService
from oie.services.lead_ranking_service import LeadRankingService
from oie.services.market_segmentation_export_service import MarketSegmentationExportService
from oie.services.market_segmentation_service import MarketSegmentationService
from oie.services.market_trends_export_service import MarketTrendsExportService
from oie.services.market_trends_service import MarketTrendsService
from oie.services.master_data_service import MasterDataService
from oie.services.master_dedup_service import MasterDedupService
from oie.services.normalization_service import NormalizationService
from oie.services.opportunity_dataset_export_service import OpportunityDatasetExportService
from oie.services.opportunity_dataset_service import OpportunityDatasetService
from oie.services.outbound_export_service import OutboundExportService
from oie.services.persistence_service import PersistenceService
from oie.services.provider_operation_metrics_export_service import ProviderOperationMetricsExportService
from oie.services.provider_operation_metrics_service import ProviderOperationMetricsService
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import ProviderExecutionService
from oie.services.opportunity_scoring_service import OpportunityScoringService
from oie.services.run_analytics_export_service import RunAnalyticsExportService
from oie.services.run_analytics_service import RunAnalyticsService
from oie.services.run_metrics_summary_export_service import RunMetricsSummaryExportService
from oie.services.run_metrics_summary_service import RunMetricsSummaryService
from oie.services.run_readiness_export_service import RunReadinessExportService
from oie.services.run_readiness_service import RunReadinessService
from oie.services.serpapi_search_service import SerpAPISearchService


@dataclass(frozen=True)
class ServiceProvider:
    ctx: RunContext
    persistence_service: PersistenceService
    persistence: PersistenceContext
    repositories: RepositoryProvider
    provider_control_service: ProviderControlService
    collection_service: CollectionService
    normalization_service: NormalizationService
    job_dedup_service: JobDedupService
    hiring_signals_service: HiringSignalsService
    master_data_service: MasterDataService
    duplicate_report_service: DuplicateReportService
    domain_review_queue_service: DomainReviewQueueService
    provider_execution_service: ProviderExecutionService
    job_intelligence_service: JobIntelligenceService
    opportunity_scoring_service: OpportunityScoringService
    lead_generation_service: LeadGenerationService
    lead_ranking_service: LeadRankingService
    db_export_service: DBExportService
    outbound_export_service: OutboundExportService
    executive_summary_service: ExecutiveSummaryService
    run_readiness_service: RunReadinessService
    collector_metrics_service: CollectorMetricsService
    collector_metrics_export_service: CollectorMetricsExportService
    collector_contribution_service: CollectorContributionService
    collector_contribution_export_service: CollectorContributionExportService
    collector_roi_service: CollectorROIService
    collector_roi_export_service: CollectorROIExportService
    run_readiness_export_service: RunReadinessExportService
    run_metrics_summary_service: RunMetricsSummaryService
    run_metrics_summary_export_service: RunMetricsSummaryExportService
    run_analytics_service: RunAnalyticsService
    run_analytics_export_service: RunAnalyticsExportService
    provider_operation_metrics_service: ProviderOperationMetricsService
    provider_operation_metrics_export_service: ProviderOperationMetricsExportService
    company_identity_service: CompanyIdentityService
    master_dedup_service: MasterDedupService
    opportunity_dataset_service: OpportunityDatasetService
    historical_intelligence_service: HistoricalIntelligenceService
    market_trends_service: MarketTrendsService
    opportunity_dataset_export_service: OpportunityDatasetExportService
    historical_export_service: HistoricalExportService
    market_trends_export_service: MarketTrendsExportService
    market_segmentation_service: MarketSegmentationService
    market_segmentation_export_service: MarketSegmentationExportService
    commercial_signal_service: CommercialSignalService
    commercial_selection_service: CommercialSelectionService
    company_identity_ai_service: CompanyIdentityAIService
    company_classification_service: CompanyClassificationService
    company_enrichment_service: CompanyEnrichmentService
    domain_ai_validation_service: DomainAIValidationService
    serpapi_search_service: SerpAPISearchService
    domain_resolution_service: DomainResolutionService

    @classmethod
    def from_run_context(cls, ctx: RunContext) -> "ServiceProvider":
        persistence_service = PersistenceService(ctx)
        provider_control_service = ProviderControlService(ctx)
        domain_ai_validation_service = DomainAIValidationService(ctx, provider_control_service)
        serpapi_search_service = SerpAPISearchService(ctx, provider_control_service)
        commercial_signal_service = CommercialSignalService()
        return cls(
            ctx=ctx,
            persistence_service=persistence_service,
            persistence=persistence_service.persistence,
            repositories=persistence_service.repositories,
            provider_control_service=provider_control_service,
            collection_service=CollectionService(ctx),
            normalization_service=NormalizationService(ctx),
            job_dedup_service=JobDedupService(ctx),
            hiring_signals_service=HiringSignalsService(ctx),
            master_data_service=MasterDataService(ctx),
            duplicate_report_service=DuplicateReportService(ctx),
            domain_review_queue_service=DomainReviewQueueService(ctx),
            provider_execution_service=ProviderExecutionService(ctx, provider_control_service),
            job_intelligence_service=JobIntelligenceService(ctx, provider_control_service),
            opportunity_scoring_service=OpportunityScoringService(ctx, provider_control_service),
            lead_generation_service=LeadGenerationService(ctx, provider_control_service),
            lead_ranking_service=LeadRankingService(ctx, provider_control_service),
            db_export_service=DBExportService(ctx, persistence=persistence_service.persistence),
            outbound_export_service=OutboundExportService(ctx, persistence=persistence_service.persistence),
            executive_summary_service=ExecutiveSummaryService(ctx, persistence=persistence_service.persistence),
            run_readiness_service=RunReadinessService(ctx, persistence=persistence_service.persistence),
            collector_metrics_service=CollectorMetricsService(ctx),
            collector_metrics_export_service=CollectorMetricsExportService(ctx),
            collector_contribution_service=CollectorContributionService(ctx),
            collector_contribution_export_service=CollectorContributionExportService(ctx),
            collector_roi_service=CollectorROIService(ctx),
            collector_roi_export_service=CollectorROIExportService(ctx),
            run_readiness_export_service=RunReadinessExportService(ctx),
            run_metrics_summary_service=RunMetricsSummaryService(ctx),
            run_metrics_summary_export_service=RunMetricsSummaryExportService(ctx),
            run_analytics_service=RunAnalyticsService(ctx),
            run_analytics_export_service=RunAnalyticsExportService(ctx),
            provider_operation_metrics_service=ProviderOperationMetricsService(ctx),
            provider_operation_metrics_export_service=ProviderOperationMetricsExportService(ctx),
            company_identity_service=CompanyIdentityService(ctx, repositories=persistence_service.repositories),
            master_dedup_service=MasterDedupService(ctx, repositories=persistence_service.repositories),
            opportunity_dataset_service=OpportunityDatasetService(ctx, repositories=persistence_service.repositories),
            historical_intelligence_service=HistoricalIntelligenceService(ctx, repositories=persistence_service.repositories),
            market_trends_service=MarketTrendsService(ctx, repositories=persistence_service.repositories),
            opportunity_dataset_export_service=OpportunityDatasetExportService(ctx),
            historical_export_service=HistoricalExportService(ctx),
            market_trends_export_service=MarketTrendsExportService(ctx),
            market_segmentation_service=MarketSegmentationService(ctx),
            market_segmentation_export_service=MarketSegmentationExportService(ctx),
            commercial_signal_service=commercial_signal_service,
            commercial_selection_service=CommercialSelectionService(commercial_signal_service),
            company_identity_ai_service=CompanyIdentityAIService(ctx, provider_control_service),
            company_classification_service=CompanyClassificationService(ctx, provider_control_service),
            company_enrichment_service=CompanyEnrichmentService(
                ctx,
                provider_control_service,
                repositories=persistence_service.repositories,
            ),
            domain_ai_validation_service=domain_ai_validation_service,
            serpapi_search_service=serpapi_search_service,
            domain_resolution_service=DomainResolutionService(
                ctx,
                provider_control_service,
                serpapi_search_service,
                domain_ai_validation_service,
            ),
        )
