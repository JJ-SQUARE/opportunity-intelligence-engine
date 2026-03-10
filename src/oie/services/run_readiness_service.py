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
                "executive_summary_json": paths.get("executive_summary_json"),
                "collector_contribution_metrics_json": paths.get("collector_contribution_metrics_json"),
                "collector_roi_metrics_json": paths.get("collector_roi_metrics_json"),
            },
        }

        self.ctx.metrics["run_readiness_ready"] = is_ready
        self.ctx.metrics["run_readiness_warnings"] = len(warnings)
        return report
