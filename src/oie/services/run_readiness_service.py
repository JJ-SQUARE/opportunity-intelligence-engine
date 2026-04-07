from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class RunReadinessService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def build_report(
        self,
        jobs: List[Dict[str, Any]],
        companies: List[Dict[str, Any]],
        leads: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        metrics = self.ctx.metrics
        paths = self.ctx.paths
        config = self.ctx.config

        enabled_collectors = []
        sources = config.get("sources", {}) or {}

        if (sources.get("google_jobs", {}) or {}).get("enabled"):
            enabled_collectors.append("google_jobs")

        discovery = sources.get("discovery", {}) or {}
        if (discovery.get("linkedin_serpapi", {}) or {}).get("enabled"):
            enabled_collectors.append("linkedin_serpapi")
        if (discovery.get("indeed_serpapi", {}) or {}).get("enabled"):
            enabled_collectors.append("indeed_serpapi")
        if (discovery.get("career_pages_serpapi", {}) or {}).get("enabled"):
            enabled_collectors.append("career_pages_serpapi")

        ats = sources.get("ats", {}) or {}
        for name in [
            "greenhouse",
            "lever",
            "workable",
            "teamtailor",
            "breezy",
            "smartrecruiters",
            "ashby",
            "recruitee",
        ]:
            if (ats.get(name, {}) or {}).get("enabled"):
                enabled_collectors.append(name)

        warnings: List[str] = []

        if not jobs:
            warnings.append("No se recolectaron jobs en la corrida.")
        if jobs and not companies:
            warnings.append("Hay jobs pero no se agregaron compañías.")
        if companies and not leads:
            warnings.append("Hay compañías pero no se generaron leads.")
        if metrics.get("jobs_without_company_key", 0) > 0:
            warnings.append("Existen jobs sin company_key asignado.")
        if len(self.ctx.provider_events) > 0:
            warnings.append("La corrida registró provider_events; revisar si hubo errores relevantes.")

        collector_error_keys = [
            key for key, value in metrics.items()
            if key.startswith("collector_") and key.endswith("_status") and str(value) == "error"
        ]
        if collector_error_keys:
            warnings.append(
                f"Se detectaron collectors con error: {', '.join(sorted(collector_error_keys))}."
            )

        rate_limit_keys = [
            key for key, value in metrics.items()
            if key.endswith("_errors_rate_limit") and int(value or 0) > 0
        ]
        if rate_limit_keys:
            warnings.append(
                f"Se detectaron rate limits en operaciones provider: {', '.join(sorted(rate_limit_keys))}."
            )

        blocked_budget_keys = [
            key for key, value in metrics.items()
            if key.endswith("_blocked_budget") and int(value or 0) > 0
        ]
        if blocked_budget_keys:
            warnings.append(
                f"Se detectaron bloqueos por presupuesto operativo: {', '.join(sorted(blocked_budget_keys))}."
            )

        blocked_provider_keys = [
            key for key, value in metrics.items()
            if key.endswith("_blocked_provider") and int(value or 0) > 0
        ]
        if blocked_provider_keys:
            warnings.append(
                f"Se detectaron bloqueos por provider/circuit breaker: {', '.join(sorted(blocked_provider_keys))}."
            )

        domain_review_queue_count = int(metrics.get("domain_review_queue_count", 0) or 0)
        if domain_review_queue_count > 0:
            warnings.append(
                f"Hay {domain_review_queue_count} compañías pendientes de revisión manual de dominio."
            )

        enrichment_attempted = [
            key for key, value in metrics.items()
            if key.endswith("_enrich_company_by_domain_started") and int(value or 0) > 0
        ]
        if enrichment_attempted and int(metrics.get("companies_enriched", 0) or 0) == 0:
            warnings.append(
                "Se intentó enrichment de compañías pero no se obtuvo ninguna enriquecida."
            )

        if bool(metrics.get("lead_generation_require_enrichment", False)):
            skipped_missing_enrichment = int(
                metrics.get("lead_generation_skipped_missing_enrichment", 0) or 0
            )
            if skipped_missing_enrichment > 0:
                warnings.append(
                    f"Lead generation exigió enrichment y dejó fuera {skipped_missing_enrichment} compañías sin enrichment."
                )

        is_ready = len(jobs) > 0 and len(companies) > 0

        report = {
            "run_id": self.ctx.run_id,
            "run_date": self.ctx.run_date,
            "is_ready_for_review": is_ready,
            "enabled_collectors": enabled_collectors,
            "jobs_count": len(jobs),
            "companies_count": len(companies),
            "leads_count": len(leads),
            "jobs_with_company_key": metrics.get("jobs_with_company_key", 0),
            "jobs_without_company_key": metrics.get("jobs_without_company_key", 0),
            "provider_events_count": len(self.ctx.provider_events),
            "warnings": warnings,
            "outputs": {
                "db_path": paths.get("db_path"),
                "jobs_export": paths.get("jobs_export"),
                "companies_export": paths.get("companies_export"),
                "leads_export": paths.get("leads_export"),
                "opportunities_export": paths.get("opportunities_export"),
                "top_opportunities_export": paths.get("top_opportunities_export"),
                "domain_review_queue_csv": paths.get("domain_review_queue_csv"),
                "provider_operation_metrics_json": paths.get("provider_operation_metrics_json"),
                "provider_operation_metrics_csv": paths.get("provider_operation_metrics_csv"),
                "collector_metrics_json": paths.get("collector_metrics_json"),
                "run_metrics_summary_json": paths.get("run_metrics_summary_json"),
                "executive_summary_json": paths.get("executive_summary_json"),
                "collector_contribution_metrics_json": paths.get("collector_contribution_metrics_json"),
                "collector_roi_metrics_json": paths.get("collector_roi_metrics_json"),
            },
        }

        self.ctx.metrics["run_readiness_ready"] = is_ready
        self.ctx.metrics["run_readiness_warnings"] = len(warnings)
        return report
