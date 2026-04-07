from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class RunAnalyticsService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

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
        items = list(companies or [])
        items.sort(key=lambda row: row.get("opportunity_score", 0) or 0, reverse=True)

        return [
            {
                "company_key": company.get("company_key"),
                "company_display": company.get("company_display"),
                "resolved_domain": company.get("resolved_domain"),
                "company_type_ai": company.get("company_type_ai"),
                "classification_confidence_ai": company.get("classification_confidence_ai"),
                "opportunity_score": company.get("opportunity_score", 0),
                "score_openings": company.get("score_openings", 0),
                "score_remote": company.get("score_remote", 0),
                "score_contractor": company.get("score_contractor", 0),
                "score_multi_source": company.get("score_multi_source", 0),
                "score_company_type": company.get("score_company_type", 0),
                "total_openings": company.get("total_openings", 0),
                "remote_jobs": company.get("remote_jobs", 0),
                "contractor_jobs": company.get("contractor_jobs", 0),
            }
            for company in items[:limit]
        ]

    def _top_leads(
        self,
        leads: List[Dict[str, Any]] | None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        items = list(leads or [])
        items.sort(
            key=lambda row: (
                row.get("lead_relevance_score", 0) or 0,
                row.get("email_quality_score", 0) or 0,
                row.get("lead_confidence", 0) or 0,
                row.get("lead_score_source", 0) or 0,
                1 if row.get("linkedin_url") else 0,
                row.get("contact_name", "") or "",
            ),
            reverse=True,
        )

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
            for lead in items[:limit]
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
            "quality": {
                "jobs_with_company_key": self.ctx.metrics.get("jobs_with_company_key", 0),
                "jobs_without_company_key": self.ctx.metrics.get("jobs_without_company_key", 0),
                "domain_review_queue_count": self.ctx.metrics.get("domain_review_queue_count", 0),
                "run_readiness_ready": run_metrics_summary.get("run_readiness_ready", False),
                "run_readiness_warnings": run_metrics_summary.get("run_readiness_warnings", 0),
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
