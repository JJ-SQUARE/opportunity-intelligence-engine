from __future__ import annotations

from typing import Any, Dict, List, Tuple

from oie.orchestration.run_context import RunContext
from oie.services.collection_service import CollectionService
from oie.services.company_classification_service import CompanyClassificationService
from oie.services.company_enrichment_service import CompanyEnrichmentService
from oie.services.company_identity_service import CompanyIdentityService
from oie.services.db_export_service import DBExportService
from oie.services.domain_resolution_service import DomainResolutionService
from oie.services.duplicate_report_service import DuplicateReportService
from oie.services.hiring_signals_service import HiringSignalsService
from oie.services.job_dedup_service import JobDedupService
from oie.services.lead_generation_service import LeadGenerationService
from oie.services.master_data_service import MasterDataService
from oie.services.master_dedup_service import MasterDedupService
from oie.services.normalization_service import NormalizationService
from oie.services.opportunity_dataset_export_service import OpportunityDatasetExportService
from oie.services.opportunity_dataset_service import OpportunityDatasetService
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
        self.master_data_service = MasterDataService(ctx)
        self.master_dedup_service = MasterDedupService(ctx)
        self.duplicate_report_service = DuplicateReportService(ctx)
        self.db_export_service = DBExportService(ctx)
        self.lead_generation_service = LeadGenerationService(ctx)
        self.opportunity_dataset_service = OpportunityDatasetService(ctx)
        self.opportunity_dataset_export_service = OpportunityDatasetExportService(ctx)
        self.company_classification_service = CompanyClassificationService(
            ctx,
            self.provider_control_service,
        )
        self.company_enrichment_service = CompanyEnrichmentService(
            ctx,
            self.provider_control_service,
        )

    def run_initial_stages(self) -> List[Dict[str, Any]]:
        jobs = self.collection_service.collect()
        jobs = self.normalization_service.normalize(jobs)
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

    def run_company_pipeline(self) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        jobs = self.run_initial_stages()
        unique_jobs, duplicate_jobs = self.master_dedup_service.dedupe_jobs_against_master(jobs)

        companies = self.hiring_signals_service.aggregate_by_company(unique_jobs)
        companies = self.domain_resolution_service.resolve_domains(companies)
        companies = self.company_identity_service.enrich_company_identity(companies)
        companies = self.company_enrichment_service.enrich_companies(companies)
        companies = self.company_classification_service.classify_companies(companies)
        companies = self.opportunity_scoring_service.score_companies(companies)

        jobs_with_company_keys = self._attach_company_keys_to_jobs(unique_jobs, companies)
        return jobs_with_company_keys, companies, duplicate_jobs

    def run(self) -> Dict[str, Any]:
        self.provider_control_service.initialize()
        self.provider_control_service.sync_budget_metrics()

        unique_jobs, companies, duplicate_jobs = self.run_company_pipeline()
        leads = self.lead_generation_service.generate_leads(companies)
        status = "company_pipeline_completed"

        self.persistence_service.persist_run_snapshot(
            status=status,
            companies=companies,
            jobs=unique_jobs,
            leads=leads,
        )

        self.master_data_service.append_jobs(unique_jobs)
        self.master_data_service.append_companies(companies)
        self.master_data_service.append_leads(leads)

        duplicate_report_rows = self.master_dedup_service.build_suspected_duplicates_report(
            jobs_duplicates=duplicate_jobs,
            leads_duplicates=[],
        )
        self.duplicate_report_service.write_suspected_duplicates_report(duplicate_report_rows)
        self.db_export_service.export_all()

        dataset = self.opportunity_dataset_service.build_dataset()
        top_dataset = self.opportunity_dataset_service.build_top_opportunities(limit=25)
        self.opportunity_dataset_export_service.export_dataset(dataset)
        self.opportunity_dataset_export_service.export_top_dataset(top_dataset)

        return {
            "run_id": self.ctx.run_id,
            "run_date": self.ctx.run_date,
            "status": status,
            "jobs_count": len(unique_jobs),
            "companies_count": len(companies),
            "leads_count": len(leads),
            "top_companies": companies[:5],
            "metrics": self.ctx.metrics,
            "budgets": self.ctx.budgets,
            "provider_events_count": len(self.ctx.provider_events),
            "db_path": self.ctx.paths.get("db_path"),
            "suspected_duplicates_report": self.ctx.paths.get("suspected_duplicates_report"),
            "companies_export": self.ctx.paths.get("companies_export"),
            "jobs_export": self.ctx.paths.get("jobs_export"),
            "leads_export": self.ctx.paths.get("leads_export"),
            "opportunities_export": self.ctx.paths.get("opportunities_export"),
            "top_opportunities_export": self.ctx.paths.get("top_opportunities_export"),
        }
