from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.services.commercial_selection_service import CommercialSelectionService
from oie.services.commercial_signal_service import CommercialSignalService


class RunAnalyticsService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.commercial_signal_service = CommercialSignalService()
        self.commercial_selection_service = CommercialSelectionService(self.commercial_signal_service)

    def _top_n(
        self,
        rows: List[Dict[str, Any]] | None,
        sort_key: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        items = list(rows or [])
        items.sort(key=lambda row: row.get(sort_key, 0) or 0, reverse=True)
        return items[:limit]

    def _top_companies(
        self,
        companies: List[Dict[str, Any]] | None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        items = self.commercial_selection_service.top_companies_analytic(companies or [], limit=limit)

        return [
            {
                "company_key": company.get("company_key"),
                "company_display": company.get("company_display"),
                "resolved_domain": company.get("resolved_domain"),
                "company_type_ai": company.get("company_type_ai"),
                "classification_confidence_ai": company.get("classification_confidence_ai"),
                "opportunity_score": company.get("opportunity_score", 0),
                "opportunity_label": company.get("opportunity_label", ""),
                "commercial_bucket": company.get("commercial_bucket", ""),
                "commercial_priority_score": company.get("commercial_priority_score", 0),
                "icp_bucket": company.get("icp_bucket", ""),
                "reachability_ready": company.get("reachability_ready", 0),
                "score_openings": company.get("score_openings", 0),
                "score_remote": company.get("score_remote", 0),
                "score_contractor": company.get("score_contractor", 0),
                "score_multi_source": company.get("score_multi_source", 0),
                "score_company_type": company.get("score_company_type", 0),
                "score_icp_fit": company.get("score_icp_fit", 0),
                "score_pain_urgency": company.get("score_pain_urgency", 0),
                "total_openings": company.get("total_openings", 0),
                "remote_jobs": company.get("remote_jobs", 0),
                "contractor_jobs": company.get("contractor_jobs", 0),
            }
            for company in items
        ]

    def _top_leads(
        self,
        leads: List[Dict[str, Any]] | None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        items = self.commercial_selection_service.top_leads(leads or [], limit=limit)

        return [
            {
                "company_key": lead.get("company_key"),
                "contact_name": lead.get("contact_name"),
                "contact_title": lead.get("contact_title"),
                "email": lead.get("email"),
                "linkedin_url": lead.get("linkedin_url"),
                "lead_source": lead.get("lead_source"),
                "lead_confidence": lead.get("lead_confidence"),
                "email_quality_score": lead.get("email_quality_score", 0),
                "lead_capture_reason": lead.get("lead_capture_reason", ""),
                "lead_relevance_score": lead.get("lead_relevance_score", 0),
                "lead_score_title": lead.get("lead_score_title", 0),
                "lead_score_source": lead.get("lead_score_source", 0),
                "lead_score_email": lead.get("lead_score_email", 0),
                "lead_score_linkedin": lead.get("lead_score_linkedin", 0),
                "lead_score_email_quality": lead.get("lead_score_email_quality", 0),
                "lead_score_confidence": lead.get("lead_score_confidence", 0),
            }
            for lead in items
        ]

    def build_analytics(
        self,
        *,
        status: str,
        jobs: List[Dict[str, Any]],
        companies: List[Dict[str, Any]],
        leads: List[Dict[str, Any]],
        duplicate_jobs: List[Dict[str, Any]],
        collector_metrics: List[Dict[str, Any]],
        collector_contribution: List[Dict[str, Any]],
        collector_roi: List[Dict[str, Any]],
        provider_operation_metrics: List[Dict[str, Any]],
        readiness_report: Dict[str, Any],
        run_metrics_summary: Dict[str, Any],
        executive_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        summary_counts_original = run_metrics_summary.get("counts_original", {}) or {}
        summary_counts_effective = run_metrics_summary.get("counts_effective", {}) or {}
        master_data_summary = run_metrics_summary.get("master_data", {}) or {}
        persistence_data_summary = run_metrics_summary.get("persistence_data", {}) or {}

        analytics = {
            "run_id": self.ctx.run_id,
            "run_date": self.ctx.run_date,
            "mode": self.ctx.mode,
            "status": status,
            "counts": {
                "jobs": len(jobs),
                "companies": len(companies),
                "leads": len(leads),
                "duplicate_jobs": len(duplicate_jobs),
            },
            "counts_original": {
                "jobs_collected_raw": summary_counts_original.get("jobs_collected_raw", self.ctx.metrics.get("jobs_collected_raw", 0)),
                "jobs_after_dedupe": summary_counts_original.get("jobs_after_dedupe", self.ctx.metrics.get("jobs_after_dedupe", 0)),
                "jobs_duplicates_detected_master": summary_counts_original.get("jobs_duplicates_detected_master", self.ctx.metrics.get("master_jobs_duplicates_detected", 0)),
                "jobs_unique_to_append_master": summary_counts_original.get("jobs_unique_to_append_master", self.ctx.metrics.get("master_jobs_unique_to_append", 0)),
                "companies_detected": summary_counts_original.get("companies_detected", self.ctx.metrics.get("companies_detected", 0)),
                "companies_after_identity_dedupe": summary_counts_original.get("companies_after_identity_dedupe", self.ctx.metrics.get("companies_after_identity_dedupe", 0)),
                "leads_generated": summary_counts_original.get("leads_generated", self.ctx.metrics.get("leads_generated", 0)),
                "best_leads_selected": summary_counts_original.get("best_leads_selected", self.ctx.metrics.get("best_leads_selected", 0)),
                "leads_duplicates_detected_master": summary_counts_original.get("leads_duplicates_detected_master", self.ctx.metrics.get("master_leads_duplicates_detected", 0)),
                "leads_unique_to_append_master": summary_counts_original.get("leads_unique_to_append_master", self.ctx.metrics.get("master_leads_unique_to_append", 0)),
            },
            "counts_effective": dict(summary_counts_effective),
            "count_deltas": dict(run_metrics_summary.get("count_deltas", {}) or {}),
            "counts_quality": dict(run_metrics_summary.get("counts_quality", {}) or {}),
            "quality": {
                "jobs_with_company_key": self.ctx.metrics.get("jobs_with_company_key", 0),
                "jobs_without_company_key": self.ctx.metrics.get("jobs_without_company_key", 0),
                "domain_review_queue_count": self.ctx.metrics.get("domain_review_queue_count", 0),
                "run_readiness_ready": run_metrics_summary.get("run_readiness_ready", False),
                "run_readiness_warnings": run_metrics_summary.get("run_readiness_warnings", 0),
                "provider_events_count": len(self.ctx.provider_events),
                "effective_jobs_vs_original_delta": max(
                    int(summary_counts_original.get("jobs_after_dedupe", 0) or 0)
                    - int(summary_counts_effective.get("jobs", 0) or 0),
                    0,
                ),
                "effective_leads_vs_selected_delta": max(
                    int(summary_counts_original.get("best_leads_selected", 0) or 0)
                    - int(summary_counts_effective.get("leads", 0) or 0),
                    0,
                ),
            },
            "top_collectors": {
                "by_jobs": self._top_n(collector_metrics, "jobs_collected", limit=5),
                "by_contribution": self._top_n(
                    collector_contribution,
                    "contribution_score",
                    limit=5,
                ),
                "by_roi": self._top_n(collector_roi, "utility_score", limit=5),
            },
            "top_companies": self._top_companies(companies, limit=10),
            "top_leads": self._top_leads(leads, limit=10),
            "provider_health": {
                "provider_errors": run_metrics_summary.get("provider_errors", {}),
                "provider_blocks": run_metrics_summary.get("provider_blocks", {}),
                "provider_operation_metrics": provider_operation_metrics,
            },
            "master_data": master_data_summary,
            "persistence_data": persistence_data_summary,
            "readiness": readiness_report,
            "run_metrics_summary": run_metrics_summary,
            "executive_summary": executive_summary,
            "artifacts": {
                "db_path": self.ctx.paths.get("db_path"),
                "jobs_export": self.ctx.paths.get("jobs_export"),
                "companies_export": self.ctx.paths.get("companies_export"),
                "leads_export": self.ctx.paths.get("leads_export"),
                "opportunities_export": self.ctx.paths.get("opportunities_export"),
                "top_opportunities_export": self.ctx.paths.get("top_opportunities_export"),
                "top_opportunities_csv": self.ctx.paths.get("top_opportunities_csv"),
                "commercial_pipeline_csv": self.ctx.paths.get("commercial_pipeline_csv"),
                "apollo_import_csv": self.ctx.paths.get("apollo_import_csv"),
                "executive_summary_json": self.ctx.paths.get("executive_summary_json"),
                "run_readiness_report_json": self.ctx.paths.get("run_readiness_report_json"),
                "run_metrics_summary_json": self.ctx.paths.get("run_metrics_summary_json"),
                "collector_metrics_json": self.ctx.paths.get("collector_metrics_json"),
                "collector_contribution_metrics_csv": self.ctx.paths.get("collector_contribution_metrics_csv"),
                "collector_contribution_metrics_json": self.ctx.paths.get("collector_contribution_metrics_json"),
                "collector_roi_metrics_csv": self.ctx.paths.get("collector_roi_metrics_csv"),
                "collector_roi_metrics_json": self.ctx.paths.get("collector_roi_metrics_json"),
                "provider_operation_metrics_csv": self.ctx.paths.get("provider_operation_metrics_csv"),
                "provider_operation_metrics_json": self.ctx.paths.get("provider_operation_metrics_json"),
            },
        }

        self.ctx.metrics["run_analytics_generated"] = True
        self.ctx.metrics["run_analytics_top_companies_count"] = len(analytics["top_companies"])
        self.ctx.metrics["run_analytics_top_leads_count"] = len(analytics["top_leads"])
        return analytics
