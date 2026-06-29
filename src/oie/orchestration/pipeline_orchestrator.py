from __future__ import annotations

import traceback
from typing import Any, Dict, List, Tuple

from oie.orchestration.run_context import RunContext
from oie.orchestration.run_manifest import finalize_manifest
from oie.services.collection_service import CollectionService
from oie.services.collector_contribution_export_service import CollectorContributionExportService
from oie.services.collector_contribution_service import CollectorContributionService
from oie.services.collector_metrics_export_service import CollectorMetricsExportService
from oie.services.collector_metrics_service import CollectorMetricsService
from oie.services.collector_roi_export_service import CollectorROIExportService
from oie.services.collector_roi_service import CollectorROIService
from oie.services.company_classification_service import CompanyClassificationService
from oie.services.company_enrichment_service import CompanyEnrichmentService
from oie.services.commercial_selection_service import CommercialSelectionService
from oie.services.commercial_signal_service import CommercialSignalService
from oie.services.company_identity_service import CompanyIdentityService
from oie.services.company_identity_ai_service import CompanyIdentityAIService
from oie.services.db_export_service import DBExportService
from oie.services.domain_resolution_service import DomainResolutionService
from oie.services.domain_ai_validation_service import DomainAIValidationService
from oie.services.duplicate_report_service import DuplicateReportService
from oie.services.executive_summary_service import ExecutiveSummaryService
from oie.services.historical_export_service import HistoricalExportService
from oie.services.historical_intelligence_service import HistoricalIntelligenceService
from oie.services.hiring_signals_service import HiringSignalsService
from oie.services.job_dedup_service import JobDedupService
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
from oie.services.opportunity_scoring_service import OpportunityScoringService
from oie.services.outbound_export_service import OutboundExportService
from oie.services.persistence_service import PersistenceService
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import ProviderExecutionService
from oie.services.provider_operation_metrics_service import ProviderOperationMetricsService
from oie.services.provider_operation_metrics_export_service import ProviderOperationMetricsExportService
from oie.services.run_readiness_export_service import RunReadinessExportService
from oie.services.run_readiness_service import RunReadinessService
from oie.services.run_metrics_summary_export_service import RunMetricsSummaryExportService
from oie.services.run_metrics_summary_service import RunMetricsSummaryService
from oie.services.run_analytics_export_service import RunAnalyticsExportService
from oie.services.run_analytics_service import RunAnalyticsService
from oie.services.serpapi_search_service import SerpAPISearchService
from oie.services.domain_review_queue_service import DomainReviewQueueService


class PipelineOrchestrator:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.collection_service = CollectionService(ctx)
        self.normalization_service = NormalizationService(ctx)
        self.job_dedup_service = JobDedupService(ctx)
        self.hiring_signals_service = HiringSignalsService(ctx)
        self.provider_control_service = ProviderControlService(ctx)
        self.job_intelligence_service = JobIntelligenceService(
            ctx,
            self.provider_control_service,
        )
        self.company_identity_ai_service = CompanyIdentityAIService(
            ctx,
            self.provider_control_service,
        )
        self.provider_execution_service = ProviderExecutionService(ctx, self.provider_control_service)
        self.domain_resolution_service = DomainResolutionService(ctx, self.provider_control_service)
        self.opportunity_scoring_service = OpportunityScoringService(
            ctx,
            self.provider_control_service,
        )
        self.persistence_service = PersistenceService(ctx)
        self.repositories = self.persistence_service.repositories
        self.company_identity_service = CompanyIdentityService(ctx, repositories=self.repositories)
        self.master_data_service = MasterDataService(ctx)
        self.master_dedup_service = MasterDedupService(ctx, repositories=self.repositories)
        self.duplicate_report_service = DuplicateReportService(ctx)
        self.domain_review_queue_service = DomainReviewQueueService(ctx)
        self.db_export_service = DBExportService(ctx, persistence=self.persistence_service.persistence)
        self.opportunity_dataset_service = OpportunityDatasetService(ctx, repositories=self.repositories)
        self.opportunity_dataset_export_service = OpportunityDatasetExportService(ctx)
        self.outbound_export_service = OutboundExportService(ctx, persistence=self.persistence_service.persistence)
        self.executive_summary_service = ExecutiveSummaryService(ctx, persistence=self.persistence_service.persistence)
        self.historical_intelligence_service = HistoricalIntelligenceService(ctx, repositories=self.repositories)
        self.historical_export_service = HistoricalExportService(ctx)
        self.market_trends_service = MarketTrendsService(ctx, repositories=self.repositories)
        self.market_trends_export_service = MarketTrendsExportService(ctx)
        self.market_segmentation_service = MarketSegmentationService(ctx)
        self.market_segmentation_export_service = MarketSegmentationExportService(ctx)
        self.collector_metrics_service = CollectorMetricsService(ctx)
        self.collector_metrics_export_service = CollectorMetricsExportService(ctx)
        self.collector_contribution_service = CollectorContributionService(ctx)
        self.collector_contribution_export_service = CollectorContributionExportService(ctx)
        self.collector_roi_service = CollectorROIService(ctx)
        self.collector_roi_export_service = CollectorROIExportService(ctx)
        self.run_readiness_service = RunReadinessService(ctx, persistence=self.persistence_service.persistence)
        self.run_readiness_export_service = RunReadinessExportService(ctx)
        self.run_metrics_summary_service = RunMetricsSummaryService(ctx)
        self.run_metrics_summary_export_service = RunMetricsSummaryExportService(ctx)
        self.run_analytics_service = RunAnalyticsService(ctx)
        self.run_analytics_export_service = RunAnalyticsExportService(ctx)
        self.provider_operation_metrics_service = ProviderOperationMetricsService(ctx)
        self.provider_operation_metrics_export_service = ProviderOperationMetricsExportService(ctx)
        self.company_classification_service = CompanyClassificationService(
            ctx,
            self.provider_control_service,
        )
        self.company_enrichment_service = CompanyEnrichmentService(
            ctx,
            self.provider_control_service,
            repositories=self.repositories,
        )
        self.commercial_signal_service = CommercialSignalService()
        self.commercial_selection_service = CommercialSelectionService(
            self.commercial_signal_service,
        )
        self.lead_generation_service = LeadGenerationService(
            ctx,
            self.provider_control_service,
        )
        self.lead_ranking_service = LeadRankingService(
            ctx,
            self.provider_control_service,
        )
        self.serpapi_search_service = SerpAPISearchService(ctx, self.provider_control_service)
        self.domain_ai_validation_service = DomainAIValidationService(
            ctx,
            self.provider_control_service,
        )
        self.domain_resolution_service = DomainResolutionService(
            ctx,
            self.provider_control_service,
            self.serpapi_search_service,
            self.domain_ai_validation_service,
        )

    def run_initial_stages(self) -> List[Dict[str, Any]]:
        jobs = self.collection_service.collect()
        jobs = self.normalization_service.normalize(jobs)
        jobs = self.job_intelligence_service.enrich_jobs(jobs)
        jobs = self.job_dedup_service.dedupe(jobs)
        return jobs

    def _build_company_lookup(
        self,
        companies: List[Dict[str, Any]],
    ) -> Dict[Tuple[str, str], str]:
        lookup: Dict[Tuple[str, str], str] = {}

        for company in companies:
            company_key = company.get("company_key")
            if not company_key:
                continue

            display = (company.get("company_display") or company.get("company") or "").strip()
            normalized = (company.get("company_normalized") or "").strip()
            resolved_domain = (company.get("resolved_domain") or "").strip()

            keys = [
                (display.lower(), resolved_domain.lower()),
                (normalized.lower(), resolved_domain.lower()),
                (display.lower(), ""),
                (normalized.lower(), ""),
            ]

            for key in keys:
                if key not in lookup:
                    lookup[key] = company_key

        return lookup

    def _attach_company_keys_to_jobs(
        self,
        jobs: List[Dict[str, Any]],
        companies: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        lookup = self._build_company_lookup(companies)
        enriched_jobs: List[Dict[str, Any]] = []
        matched_jobs = 0

        for job in jobs:
            record = dict(job)
            company_name = (record.get("company") or "").strip()
            normalized_name = self.company_identity_service.normalize_company_name(company_name)

            candidates = [
                (company_name.lower(), ""),
                (normalized_name.lower(), ""),
            ]

            matched_company_key = None
            for candidate in candidates:
                matched_company_key = lookup.get(candidate)
                if matched_company_key:
                    break

            if matched_company_key:
                record["company_key"] = matched_company_key
                matched_jobs += 1

            enriched_jobs.append(record)

        self.ctx.metrics["jobs_with_company_key"] = matched_jobs
        self.ctx.metrics["jobs_without_company_key"] = max(len(jobs) - matched_jobs, 0)
        return enriched_jobs

    def _limit_companies_for_run(
        self,
        companies: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        raw_limit = self.ctx.flags.get("limit")
        sorted_companies = self.commercial_selection_service.sort_companies(companies)
        actionable_companies = self.commercial_selection_service.commercially_actionable_companies(
            sorted_companies
        )

        self.ctx.metrics["companies_commercial_candidates"] = len(actionable_companies)
        self.ctx.metrics["companies_commercial_filtered_out"] = max(
            len(sorted_companies) - len(actionable_companies),
            0,
        )

        # No usar el commercial gate como filtro duro antes de persistir/exportar.
        # La priorización comercial sigue viva en commercial_bucket/commercial_priority_score,
        # pero el --limit ahora toma del ranking analítico completo para no perder señales útiles.
        selection_pool = sorted_companies
        used_commercial_gate = False
        self.ctx.metrics["companies_limit_used_analytic_fallback"] = bool(sorted_companies)
        self.ctx.metrics["companies_limit_commercial_gate_soft_only"] = True

        if raw_limit in (None, "", 0, "0", False):
            self.ctx.metrics["companies_limit_requested"] = 0
            self.ctx.metrics["companies_limit_applied"] = len(selection_pool)
            self.ctx.metrics["companies_limit_truncated"] = 0
            self.ctx.metrics["companies_limit_used_commercial_gate"] = used_commercial_gate
            return selection_pool

        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            self.ctx.metrics["companies_limit_invalid"] = True
            self.ctx.metrics["companies_limit_requested"] = 0
            self.ctx.metrics["companies_limit_applied"] = len(selection_pool)
            self.ctx.metrics["companies_limit_truncated"] = 0
            self.ctx.metrics["companies_limit_used_commercial_gate"] = used_commercial_gate
            return selection_pool

        if limit <= 0:
            self.ctx.metrics["companies_limit_requested"] = limit
            self.ctx.metrics["companies_limit_applied"] = 0
            self.ctx.metrics["companies_limit_truncated"] = len(selection_pool)
            self.ctx.metrics["companies_limit_used_commercial_gate"] = used_commercial_gate
            return []

        limited = selection_pool[:limit]
        self.ctx.metrics["companies_limit_requested"] = limit
        self.ctx.metrics["companies_limit_applied"] = len(limited)
        self.ctx.metrics["companies_limit_truncated"] = max(len(selection_pool) - len(limited), 0)
        self.ctx.metrics["companies_limit_used_commercial_gate"] = used_commercial_gate
        return limited


    def _competitor_patterns_from_config(self) -> List[str]:
        patterns: List[str] = []

        candidates = [
            ((self.ctx.config.get("benchmark", {}) or {}).get("competitors")),
            ((self.ctx.config.get("commercial", {}) or {}).get("benchmark_competitors")),
            self.ctx.config.get("competitors"),
        ]

        for candidate in candidates:
            if not candidate:
                continue

            if isinstance(candidate, str):
                value = candidate.strip().lower()
                if value:
                    patterns.append(value)
                continue

            if isinstance(candidate, dict):
                for key in ("name", "domain", "company", "website"):
                    value = str(candidate.get(key) or "").strip().lower()
                    if value:
                        patterns.append(value)
                continue

            if isinstance(candidate, list):
                for item in candidate:
                    if isinstance(item, str):
                        value = item.strip().lower()
                        if value:
                            patterns.append(value)
                    elif isinstance(item, dict):
                        for key in ("name", "domain", "company", "website"):
                            value = str(item.get(key) or "").strip().lower()
                            if value:
                                patterns.append(value)

        deduped: List[str] = []
        seen = set()
        for pattern in patterns:
            if pattern not in seen:
                seen.add(pattern)
                deduped.append(pattern)

        return deduped

    def _split_benchmark_competitors(
        self,
        companies: List[Dict[str, Any]],
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        patterns = self._competitor_patterns_from_config()
        if not patterns:
            self.ctx.metrics["benchmark_competitors_detected"] = 0
            return companies, []

        actionable: List[Dict[str, Any]] = []
        benchmark: List[Dict[str, Any]] = []

        for company in companies:
            record = dict(company)

            haystacks = [
                str(record.get("company_display") or "").strip().lower(),
                str(record.get("company") or "").strip().lower(),
                str(record.get("company_normalized") or "").strip().lower(),
                str(record.get("resolved_domain") or "").strip().lower(),
                str(record.get("linkedin_company_url") or "").strip().lower(),
            ]
            blob = " | ".join(v for v in haystacks if v)

            is_competitor = any(pattern and pattern in blob for pattern in patterns)
            if is_competitor:
                record["benchmark_only"] = True
                record["company_type_ai"] = "competitor"
                record["classification_confidence_ai"] = 1.0
                record["classification_source"] = "config_benchmark_competitor"
                record.setdefault("opportunity_label", "benchmark")
                benchmark.append(record)
            else:
                actionable.append(record)

        self.ctx.metrics["benchmark_competitors_detected"] = len(benchmark)
        return actionable, benchmark

    def _companies_for_lead_generation(
        self,
        companies: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        filtered: List[Dict[str, Any]] = []
        skipped = 0

        for company in companies:
            company_type = str(company.get("company_type_ai") or "").strip().lower()
            if company.get("benchmark_only") or company_type == "competitor":
                skipped += 1
                continue
            filtered.append(company)

        self.ctx.metrics["benchmark_competitors_skipped_for_leads"] = skipped
        return filtered

    def _apply_ai_company_gate(
        self,
        companies: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        advanced: List[Dict[str, Any]] = []
        rejected = 0
        hard_reject_types = {"job_board", "marketplace", "staffing", "staffing_agency", "confidential", "noise", "generic"}

        for company in companies:
            record = dict(company)
            gate_type = str(record.get("ai_company_gate_company_type") or "").strip().lower()
            gate_relevance = str(record.get("ai_company_gate_relevance") or "").strip().lower()
            should_advance = record.get("ai_company_gate_should_advance")

            hard_reject = gate_type in hard_reject_types
            soft_reject = should_advance is False and gate_relevance not in {"medium", "high"}

            if hard_reject or soft_reject:
                rejected += 1
                record["company_identity_ai_discarded"] = True
                self.ctx.metrics[f"companies_rejected_by_ai_{gate_type or 'unknown'}"] = (
                    int(self.ctx.metrics.get(f"companies_rejected_by_ai_{gate_type or 'unknown'}", 0) or 0) + 1
                )
                continue

            advanced.append(record)

        self.ctx.metrics["companies_rejected_by_ai"] = rejected
        self.ctx.metrics["companies_advanced_by_ai"] = len(advanced)
        return advanced

    def run_company_pipeline(self) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        self.persistence_service.initialize()
        jobs = self.run_initial_stages()
        unique_jobs, duplicate_jobs = self.master_dedup_service.dedupe_jobs_against_master(jobs)

        companies = self.hiring_signals_service.aggregate_by_company(unique_jobs)
        actionable_companies, benchmark_companies = self._split_benchmark_competitors(companies)
        actionable_companies = self._apply_ai_company_gate(actionable_companies)

        actionable_companies = self.company_identity_ai_service.enrich_companies(actionable_companies)
        actionable_companies = self.domain_resolution_service.resolve_domains(actionable_companies)
        actionable_companies = self.company_identity_service.enrich_company_identity(actionable_companies)
        actionable_companies = self.company_enrichment_service.enrich_companies(actionable_companies)
        actionable_companies = self.company_classification_service.classify_companies(actionable_companies)
        actionable_companies = self.opportunity_scoring_service.score_companies(actionable_companies)
        actionable_companies = self._limit_companies_for_run(actionable_companies)

        companies = actionable_companies + benchmark_companies
        jobs_with_company_keys = self._attach_company_keys_to_jobs(unique_jobs, companies)

        allowed_company_keys = {
            company.get("company_key")
            for company in companies
            if company.get("company_key")
        }
        jobs_with_company_keys = [
            job for job in jobs_with_company_keys
            if job.get("company_key") in allowed_company_keys
        ]

        self.ctx.metrics["jobs_with_company_key"] = len(jobs_with_company_keys)
        self.ctx.metrics["jobs_without_company_key"] = 0
        self.ctx.metrics["jobs_after_company_limit"] = len(jobs_with_company_keys)

        return jobs_with_company_keys, companies, duplicate_jobs

    def run(self) -> Dict[str, Any]:
        unique_jobs: List[Dict[str, Any]] = []
        companies: List[Dict[str, Any]] = []
        duplicate_jobs: List[Dict[str, Any]] = []
        best_leads: List[Dict[str, Any]] = []
        duplicate_leads: List[Dict[str, Any]] = []
        run_metrics_summary: Dict[str, Any] | None = None
        run_analytics: Dict[str, Any] | None = None
        executive_summary: Dict[str, Any] | None = None
        status = "failed"

        try:
            self.provider_control_service.initialize()
            self.provider_control_service.sync_budget_metrics()

            unique_jobs, companies, duplicate_jobs = self.run_company_pipeline()
            leads = self.lead_generation_service.generate_leads(self._companies_for_lead_generation(companies))
            ranked_leads = self.lead_ranking_service.rank_leads(leads)

            lead_cfg = self.ctx.config.get("lead_generation", {}) or {}
            max_selected_leads_per_company = int(
                lead_cfg.get("max_selected_leads_per_company", 3) or 3
            )
            max_selected_leads_per_company = max(1, max_selected_leads_per_company)

            best_leads = self.lead_ranking_service.select_top_leads_per_company(
                ranked_leads,
                max_leads_per_company=max_selected_leads_per_company,
            )
            self.ctx.metrics["pipeline_selected_leads_per_company"] = max_selected_leads_per_company

            best_leads, duplicate_leads = self.master_dedup_service.dedupe_leads_against_master(best_leads)

            status = "company_pipeline_completed"

            self.persistence_service.persist_run_snapshot(
                status=status,
                companies=companies,
                jobs=unique_jobs,
                leads=best_leads,
            )

            self.master_data_service.append_jobs(unique_jobs)
            self.master_data_service.append_companies(companies)
            self.master_data_service.append_leads(best_leads)

            duplicate_report_rows = self.master_dedup_service.build_suspected_duplicates_report(
                jobs_duplicates=duplicate_jobs,
                leads_duplicates=duplicate_leads,
            )
            self.duplicate_report_service.write_suspected_duplicates_report(duplicate_report_rows)
            self.domain_review_queue_service.export_csv(companies)
            self.db_export_service.export_all()

            dataset = self.opportunity_dataset_service.build_dataset()
            top_dataset = self.opportunity_dataset_service.build_top_opportunities(limit=25)
            self.opportunity_dataset_export_service.export_dataset(dataset)
            self.opportunity_dataset_export_service.export_top_dataset(top_dataset)
            self.outbound_export_service.export_all()
            hubspot_push_result = self.outbound_export_service.push_hubspot_payloads(
                self.provider_execution_service
            )
            self.ctx.provider_state["hubspot_push_result"] = hubspot_push_result

            executive_summary = self.executive_summary_service.build_summary(companies, best_leads)
            self.executive_summary_service.write_summary(executive_summary)

            historical_rows = self.historical_intelligence_service.build_company_hiring_history()
            growth_rows = self.historical_intelligence_service.build_company_growth_summary()
            self.historical_export_service.export_company_history(historical_rows)
            self.historical_export_service.export_growth_summary(growth_rows)
            self.historical_export_service.export_summary_json(growth_rows)

            source_trends = self.market_trends_service.build_source_trends()
            country_trends = self.market_trends_service.build_country_trends()
            new_companies_trends = self.market_trends_service.build_new_companies_by_source()
            market_summary = self.market_trends_service.build_summary()

            self.market_trends_export_service.export_source_trends(source_trends)
            self.market_trends_export_service.export_country_trends(country_trends)
            self.market_trends_export_service.export_new_companies_by_source(new_companies_trends)
            self.market_trends_export_service.export_summary_json(market_summary)

            segmented_companies = self.market_segmentation_service.segment_companies(companies)
            market_segment_summary = self.market_segmentation_service.build_segment_summary(companies)
            self.market_segmentation_export_service.export_segmented_companies(segmented_companies)
            self.market_segmentation_export_service.export_segment_summary(market_segment_summary)
            self.market_segmentation_export_service.export_segment_summary_json(market_segment_summary)

            collector_metrics = self.collector_metrics_service.build_metrics(unique_jobs, companies)
            self.collector_metrics_export_service.export_json(collector_metrics)

            collector_contribution = self.collector_contribution_service.build_contribution_metrics(
                unique_jobs,
                companies,
                best_leads,
            )
            self.collector_contribution_export_service.export_csv(collector_contribution)
            self.collector_contribution_export_service.export_json(collector_contribution)

            collector_roi = self.collector_roi_service.build_roi_metrics(
                unique_jobs=unique_jobs,
                duplicate_jobs=duplicate_jobs,
                companies=companies,
                leads=best_leads,
            )
            self.collector_roi_export_service.export_csv(collector_roi)
            self.collector_roi_export_service.export_json(collector_roi)

            provider_operation_metrics = self.provider_operation_metrics_service.build_rows()
            self.provider_operation_metrics_export_service.export_csv(provider_operation_metrics)
            self.provider_operation_metrics_export_service.export_json(provider_operation_metrics)

            self.ctx.provider_state["run_metrics_summary_counts"] = {
                "jobs_count": len(unique_jobs),
                "companies_count": len(companies),
                "leads_count": len(best_leads),
            }

            run_metrics_summary = self.run_metrics_summary_service.build_summary()
            self.run_metrics_summary_export_service.export_json(run_metrics_summary)

            readiness_report = self.run_readiness_service.build_report(
                jobs=unique_jobs,
                companies=companies,
                leads=best_leads,
            )
            self.run_readiness_export_service.export_json(readiness_report)

            run_metrics_summary = self.run_metrics_summary_service.build_summary()
            self.run_metrics_summary_export_service.export_json(run_metrics_summary)

            run_analytics = self.run_analytics_service.build_analytics(
                status=status,
                jobs=unique_jobs,
                companies=companies,
                leads=best_leads,
                duplicate_jobs=duplicate_jobs,
                collector_metrics=collector_metrics,
                collector_contribution=collector_contribution,
                collector_roi=collector_roi,
                provider_operation_metrics=provider_operation_metrics,
                readiness_report=readiness_report,
                run_metrics_summary=run_metrics_summary,
                executive_summary=executive_summary,
            )
            self.run_analytics_export_service.export_json(run_analytics)
            finalize_manifest(self.ctx, "completed")

            return {
                "run_id": self.ctx.run_id,
                "run_date": self.ctx.run_date,
                "status": status,
                "jobs_count": len(unique_jobs),
                "companies_count": len(companies),
                "leads_count": len(best_leads),
                "top_companies": companies[:5],
                "metrics": self.ctx.metrics,
                "budgets": self.ctx.budgets,
                "provider_events_count": len(self.ctx.provider_events),

                "db_path": self.ctx.paths.get("db_path"),

                "suspected_duplicates_report": self.ctx.paths.get("suspected_duplicates_report"),
                "domain_review_queue_csv": self.ctx.paths.get("domain_review_queue_csv"),
                "companies_export": self.ctx.paths.get("companies_export"),
                "jobs_export": self.ctx.paths.get("jobs_export"),
                "leads_export": self.ctx.paths.get("leads_export"),
                "opportunities_export": self.ctx.paths.get("opportunities_export"),
                "top_opportunities_export": self.ctx.paths.get("top_opportunities_export"),
                "commercial_pipeline_csv": self.ctx.paths.get("commercial_pipeline_csv"),
                "commercial_report_md": self.ctx.paths.get("commercial_report_md"),
                "apollo_import_csv": self.ctx.paths.get("apollo_import_csv"),
                "hubspot_companies_json": self.ctx.paths.get("hubspot_companies_json"),
                "hubspot_contacts_json": self.ctx.paths.get("hubspot_contacts_json"),
                "hubspot_tasks_json": self.ctx.paths.get("hubspot_tasks_json"),
                "hubspot_notes_json": self.ctx.paths.get("hubspot_notes_json"),
                "hubspot_sync_results_json": self.ctx.paths.get("hubspot_sync_results_json"),
                "top_opportunities_csv": self.ctx.paths.get("top_opportunities_csv"),

                "executive_summary_json": self.ctx.paths.get("executive_summary_json"),
                "run_readiness_report_json": self.ctx.paths.get("run_readiness_report_json"),
                "run_metrics_summary_json": self.ctx.paths.get("run_metrics_summary_json"),
                "run_analytics_json": self.ctx.paths.get("run_analytics_json"),

                "historical_company_hiring_csv": self.ctx.paths.get("historical_company_hiring_csv"),
                "historical_growth_summary_csv": self.ctx.paths.get("historical_growth_summary_csv"),
                "historical_summary_json": self.ctx.paths.get("historical_summary_json"),

                "market_trends_by_source_csv": self.ctx.paths.get("market_trends_by_source_csv"),
                "market_trends_by_location_csv": self.ctx.paths.get("market_trends_by_location_csv"),
                "market_new_companies_by_source_csv": self.ctx.paths.get("market_new_companies_by_source_csv"),
                "market_trends_summary_json": self.ctx.paths.get("market_trends_summary_json"),

                "market_segmented_companies_csv": self.ctx.paths.get("market_segmented_companies_csv"),
                "market_segment_summary_csv": self.ctx.paths.get("market_segment_summary_csv"),
                "market_segment_summary_json": self.ctx.paths.get("market_segment_summary_json"),

                "collector_metrics_json": self.ctx.paths.get("collector_metrics_json"),
                "collector_contribution_metrics_csv": self.ctx.paths.get("collector_contribution_metrics_csv"),
                "collector_contribution_metrics_json": self.ctx.paths.get("collector_contribution_metrics_json"),
                "collector_roi_metrics_csv": self.ctx.paths.get("collector_roi_metrics_csv"),
                "collector_roi_metrics_json": self.ctx.paths.get("collector_roi_metrics_json"),

                "provider_operation_metrics_csv": self.ctx.paths.get("provider_operation_metrics_csv"),
                "provider_operation_metrics_json": self.ctx.paths.get("provider_operation_metrics_json"),

                "run_metrics_summary": run_metrics_summary,
                "executive_summary": executive_summary,
                "run_analytics": run_analytics,
            }

        except Exception as exc:
            self.ctx.metrics["pipeline_failed"] = True
            self.ctx.metrics["pipeline_error_type"] = exc.__class__.__name__
            self.ctx.metrics["pipeline_error_message"] = str(exc)
            self.ctx.provider_state["pipeline_error"] = {
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
                "traceback": traceback.format_exc(),
            }

            self.ctx.add_provider_event(
                provider="pipeline",
                event_type="run_failed",
                message=str(exc),
                metadata={
                    "error_type": exc.__class__.__name__,
                },
            )

            try:
                finalize_manifest(
                    self.ctx,
                    "failed",
                    {
                        "error_type": exc.__class__.__name__,
                        "error_message": str(exc),
                    },
                )
            except Exception:
                self.ctx.metrics["pipeline_failure_finalize_manifest_failed"] = True

            try:
                self.persistence_service.persist_run_snapshot(
                    status=status,
                    companies=companies,
                    jobs=unique_jobs,
                    leads=best_leads,
                )
            except Exception:
                self.ctx.metrics["pipeline_failure_persist_snapshot_failed"] = True

            raise