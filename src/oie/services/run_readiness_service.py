from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.services.commercial_signal_service import CommercialSignalService


class RunReadinessService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.commercial_signal_service = CommercialSignalService()

    def _int_metric(self, key: str) -> int:
        value = self.ctx.metrics.get(key, 0)
        try:
            return int(value or 0)
        except Exception:
            return 0

    def _bool_metric(self, key: str) -> bool:
        value = self.ctx.metrics.get(key, False)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def _has_output_artifact(self, paths: Dict[str, Any], key: str) -> bool:
        value = str(paths.get(key) or "").strip()
        return bool(value)

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

        counts_original = self.ctx.provider_state.get("run_metrics_summary_counts_original") or {}
        counts_effective = self.ctx.provider_state.get("run_metrics_summary_counts_effective") or {}

        strong_icp_companies = 0
        strong_icp_without_reachability = 0
        for company in companies:
            finalized_company = self.commercial_signal_service.finalize_row(company)
            icp_bucket = str(finalized_company.get("icp_bucket") or "")
            has_reachability = bool(int(finalized_company.get("reachability_ready", 0) or 0))

            if icp_bucket == "strong_icp":
                strong_icp_companies += 1
                if not has_reachability:
                    strong_icp_without_reachability += 1

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

        auth_error_keys = [
            key for key, value in metrics.items()
            if key.endswith("_errors_auth") and int(value or 0) > 0
        ]
        if auth_error_keys:
            warnings.append(
                f"Se detectaron errores de autenticación/permisos en providers: {', '.join(sorted(auth_error_keys))}."
            )

        permission_error_keys = [
            key for key, value in metrics.items()
            if key.endswith("_errors_permission") and int(value or 0) > 0
        ]
        if permission_error_keys:
            warnings.append(
                f"Se detectaron errores explícitos de permisos en providers: {', '.join(sorted(permission_error_keys))}."
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

        if strong_icp_without_reachability > 0:
            warnings.append(
                f"Hay {strong_icp_without_reachability} compañías strong ICP sin reachability suficiente para outreach."
            )

        original_jobs_after_dedupe = int(
            counts_original.get("jobs_after_dedupe", metrics.get("jobs_after_dedupe", len(jobs))) or 0
        )
        effective_jobs = int(
            counts_effective.get("jobs", metrics.get("master_jobs_unique_to_append", len(jobs))) or 0
        )
        original_leads_selected = int(
            counts_original.get("best_leads_selected", metrics.get("best_leads_selected", len(leads))) or 0
        )
        effective_leads = int(
            counts_effective.get("leads", metrics.get("master_leads_unique_to_append", len(leads))) or 0
        )

        if original_jobs_after_dedupe > 0 and effective_jobs < original_jobs_after_dedupe:
            warnings.append(
                f"El volumen efectivo de jobs ({effective_jobs}) quedó por debajo del volumen post-dedupe ({original_jobs_after_dedupe})."
            )

        if original_leads_selected > 0 and effective_leads < original_leads_selected:
            warnings.append(
                f"El volumen efectivo de leads ({effective_leads}) quedó por debajo de los leads seleccionados ({original_leads_selected})."
            )

        persistence_errors_count = self._int_metric("persistence_errors_count")
        master_schema_errors_count = self._int_metric("master_schema_errors_count")
        if persistence_errors_count > 0:
            warnings.append(
                f"Se detectaron {persistence_errors_count} errores de persistencia durante la corrida."
            )
        if master_schema_errors_count > 0:
            warnings.append(
                f"Se detectaron {master_schema_errors_count} errores de schema al escribir master data."
            )

        if self._bool_metric("persistence_companies_attempted") and not self._bool_metric("persistence_companies_succeeded"):
            warnings.append("La persistencia de companies no se completó correctamente.")
        if self._bool_metric("persistence_jobs_attempted") and not self._bool_metric("persistence_jobs_succeeded"):
            warnings.append("La persistencia de jobs no se completó correctamente.")
        if self._bool_metric("persistence_leads_attempted") and not self._bool_metric("persistence_leads_succeeded"):
            warnings.append("La persistencia de leads no se completó correctamente.")

        expected_output_keys = [
            "jobs_export",
            "companies_export",
            "leads_export",
            "commercial_pipeline_csv",
            "apollo_import_csv",
            "commercial_report_md",
            "run_metrics_summary_json",
        ]
        missing_outputs = [key for key in expected_output_keys if not self._has_output_artifact(paths, key)]
        if missing_outputs:
            warnings.append(
                f"Faltan artefactos de salida esperados: {', '.join(sorted(missing_outputs))}."
            )

        run_useful = bool(jobs) and bool(companies)
        is_ready = (
            run_useful
            and persistence_errors_count == 0
            and master_schema_errors_count == 0
            and not missing_outputs
        )

        report = {
            "run_id": self.ctx.run_id,
            "run_date": self.ctx.run_date,
            "is_ready_for_review": is_ready,
            "run_useful": run_useful,
            "enabled_collectors": enabled_collectors,
            "jobs_count": len(jobs),
            "companies_count": len(companies),
            "leads_count": len(leads),
            "jobs_with_company_key": metrics.get("jobs_with_company_key", 0),
            "jobs_without_company_key": metrics.get("jobs_without_company_key", 0),
            "provider_events_count": len(self.ctx.provider_events),
            "warnings": warnings,
            "counts_original": {
                "jobs_after_dedupe": original_jobs_after_dedupe,
                "best_leads_selected": original_leads_selected,
            },
            "counts_effective": {
                "jobs": effective_jobs,
                "companies": int(counts_effective.get("companies", len(companies)) or 0),
                "leads": effective_leads,
            },
            "icp_reachability_summary": {
                "strong_icp_companies": strong_icp_companies,
                "strong_icp_without_reachability": strong_icp_without_reachability,
            },
            "persistence_summary": {
                "errors_count": persistence_errors_count,
                "master_schema_errors_count": master_schema_errors_count,
                "companies_succeeded": self._bool_metric("persistence_companies_succeeded"),
                "jobs_succeeded": self._bool_metric("persistence_jobs_succeeded"),
                "leads_succeeded": self._bool_metric("persistence_leads_succeeded"),
            },
            "export_summary": {
                "expected_outputs": expected_output_keys,
                "missing_outputs": missing_outputs,
            },
            "outputs": {
                "db_path": paths.get("db_path"),
                "jobs_export": paths.get("jobs_export"),
                "companies_export": paths.get("companies_export"),
                "leads_export": paths.get("leads_export"),
                "opportunities_export": paths.get("opportunities_export"),
                "top_opportunities_export": paths.get("top_opportunities_export"),
                "commercial_pipeline_csv": paths.get("commercial_pipeline_csv"),
                "apollo_import_csv": paths.get("apollo_import_csv"),
                "commercial_report_md": paths.get("commercial_report_md"),
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
        self.ctx.metrics["run_readiness_useful"] = run_useful
        self.ctx.metrics["run_readiness_warnings"] = len(warnings)
        self.ctx.metrics["run_readiness_missing_outputs"] = len(missing_outputs)
        return report
