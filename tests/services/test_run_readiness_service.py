from oie.orchestration.run_context import RunContext
from oie.services.run_readiness_service import RunReadinessService


def test_run_readiness_service_builds_report():
    ctx = RunContext.create(
        config={
            "sources": {
                "google_jobs": {"enabled": True},
                "discovery": {"linkedin_serpapi": {"enabled": True}},
                "ats": {"greenhouse": {"enabled": True}},
            }
        },
        flags={},
    )
    ctx.metrics["jobs_with_company_key"] = 2
    ctx.metrics["jobs_without_company_key"] = 1
    ctx.paths["jobs_export"] = "/tmp/jobs_export.csv"
    ctx.paths["companies_export"] = "/tmp/companies_export.csv"
    ctx.paths["leads_export"] = "/tmp/leads_export.csv"
    ctx.paths["commercial_pipeline_csv"] = "/tmp/commercial_pipeline.csv"
    ctx.paths["apollo_import_csv"] = "/tmp/apollo_import.csv"
    ctx.paths["commercial_report_md"] = "/tmp/commercial_report.md"
    ctx.paths["run_metrics_summary_json"] = "/tmp/run_metrics_summary.json"

    service = RunReadinessService(ctx)

    report = service.build_report(
        jobs=[{"title": "Backend Engineer"}],
        companies=[{"company_key": "cmp_a"}],
        leads=[],
    )

    assert report["is_ready_for_review"] is True
    assert report["run_useful"] is True
    assert "google_jobs" in report["enabled_collectors"]
    assert report["jobs_count"] == 1
    assert report["companies_count"] == 1
    assert report["leads_count"] == 0
    assert report["jobs_without_company_key"] == 1
    assert "collector_metrics_json" in report["outputs"]
    assert "run_metrics_summary_json" in report["outputs"]
    assert "commercial_pipeline_csv" in report["outputs"]
    assert "apollo_import_csv" in report["outputs"]
    assert len(report["warnings"]) >= 1


def test_run_readiness_service_includes_operational_warnings():
    ctx = RunContext.create(
        config={
            "sources": {
                "google_jobs": {"enabled": True},
            }
        },
        flags={},
    )
    ctx.metrics["jobs_with_company_key"] = 5
    ctx.metrics["jobs_without_company_key"] = 0
    ctx.metrics["domain_review_queue_count"] = 3
    ctx.metrics["companies_enriched"] = 0
    ctx.metrics["apollo_enrich_company_by_domain_started"] = 2
    ctx.metrics["openai_classify_company_blocked_budget"] = 4
    ctx.metrics["hunter_search_domain_contacts_blocked_provider"] = 7

    service = RunReadinessService(ctx)
    report = service.build_report(
        jobs=[{"title": "Backend Engineer"}],
        companies=[{"company_key": "cmp_a"}],
        leads=[{"company_key": "cmp_a"}],
    )

    warnings = " | ".join(report["warnings"])
    assert "bloqueos por presupuesto operativo" in warnings
    assert "bloqueos por provider/circuit breaker" in warnings
    assert "pendientes de revisión manual de dominio" in warnings
    assert "no se obtuvo ninguna enriquecida" in warnings


def test_run_readiness_service_warns_when_lead_generation_requires_enrichment_and_skips_companies():
    ctx = RunContext.create(
        config={
            "sources": {
                "google_jobs": {"enabled": True},
            }
        },
        flags={},
    )
    ctx.metrics["jobs_with_company_key"] = 3
    ctx.metrics["jobs_without_company_key"] = 0
    ctx.metrics["lead_generation_require_enrichment"] = True
    ctx.metrics["lead_generation_skipped_missing_enrichment"] = 2

    service = RunReadinessService(ctx)
    report = service.build_report(
        jobs=[{"title": "Backend Engineer"}],
        companies=[{"company_key": "cmp_a"}],
        leads=[{"company_key": "cmp_a"}],
    )

    warnings = " | ".join(report["warnings"])
    assert "Lead generation exigió enrichment" in warnings
    assert "2 compañías sin enrichment" in warnings


def test_run_readiness_service_reports_strong_icp_without_reachability():
    ctx = RunContext.create(
        config={
            "sources": {
                "google_jobs": {"enabled": True},
            }
        },
        flags={},
    )
    ctx.metrics["jobs_with_company_key"] = 2
    ctx.metrics["jobs_without_company_key"] = 0

    service = RunReadinessService(ctx)
    report = service.build_report(
        jobs=[{"title": "Backend Engineer"}],
        companies=[
            {
                "company_key": "cmp_a",
                "company_type_ai": "end_client",
                "opportunity_score": 72,
                "domain_validation_status": "rejected",
                "resolved_domain": "",
                "linkedin_company_url": "",
                "enrichment_source": "",
            }
        ],
        leads=[],
    )

    warnings = " | ".join(report["warnings"])
    assert "strong ICP sin reachability suficiente" in warnings
    assert report["icp_reachability_summary"]["strong_icp_companies"] == 1
    assert report["icp_reachability_summary"]["strong_icp_without_reachability"] == 1


def test_run_readiness_service_uses_provider_state_effective_and_original_counts():
    ctx = RunContext.create(
        config={
            "sources": {
                "google_jobs": {"enabled": True},
            }
        },
        flags={},
    )
    ctx.metrics["jobs_with_company_key"] = 3
    ctx.metrics["jobs_without_company_key"] = 0
    ctx.provider_state["run_metrics_summary_counts_original"] = {
        "jobs_after_dedupe": 10,
        "best_leads_selected": 4,
    }
    ctx.provider_state["run_metrics_summary_counts_effective"] = {
        "jobs": 7,
        "companies": 2,
        "leads": 2,
    }

    service = RunReadinessService(ctx)
    report = service.build_report(
        jobs=[{"title": "Backend Engineer"}],
        companies=[{"company_key": "cmp_a"}, {"company_key": "cmp_b"}],
        leads=[{"company_key": "cmp_a"}, {"company_key": "cmp_b"}],
    )

    warnings = " | ".join(report["warnings"])
    assert "volumen efectivo de jobs (7)" in warnings
    assert "volumen efectivo de leads (2)" in warnings
    assert report["counts_original"]["jobs_after_dedupe"] == 10
    assert report["counts_original"]["best_leads_selected"] == 4
    assert report["counts_effective"]["jobs"] == 7
    assert report["counts_effective"]["companies"] == 2
    assert report["counts_effective"]["leads"] == 2


def test_run_readiness_service_flags_persistence_and_missing_outputs():
    ctx = RunContext.create(
        config={
            "sources": {
                "google_jobs": {"enabled": True},
            }
        },
        flags={},
    )
    ctx.metrics["jobs_with_company_key"] = 2
    ctx.metrics["jobs_without_company_key"] = 0
    ctx.metrics["persistence_errors_count"] = 2
    ctx.metrics["master_schema_errors_count"] = 1
    ctx.metrics["persistence_companies_attempted"] = True
    ctx.metrics["persistence_companies_succeeded"] = False
    ctx.metrics["persistence_jobs_attempted"] = True
    ctx.metrics["persistence_jobs_succeeded"] = True
    ctx.metrics["persistence_leads_attempted"] = True
    ctx.metrics["persistence_leads_succeeded"] = False
    ctx.paths["jobs_export"] = "/tmp/jobs_export.csv"

    service = RunReadinessService(ctx)
    report = service.build_report(
        jobs=[{"title": "Backend Engineer"}],
        companies=[{"company_key": "cmp_a"}],
        leads=[{"company_key": "cmp_a"}],
    )

    warnings = " | ".join(report["warnings"])
    assert report["run_useful"] is True
    assert report["is_ready_for_review"] is False
    assert "errores de persistencia" in warnings
    assert "errores de schema" in warnings
    assert "persistencia de companies no se completó correctamente" in warnings
    assert "persistencia de leads no se completó correctamente" in warnings
    assert "Faltan artefactos de salida esperados" in warnings
    assert "companies_export" in report["export_summary"]["missing_outputs"]
    assert report["persistence_summary"]["errors_count"] == 2
    assert report["persistence_summary"]["master_schema_errors_count"] == 1


def test_run_readiness_service_uses_shared_reachability_signal_for_email_only_company():
    ctx = RunContext.create(
        config={
            "sources": {
                "google_jobs": {"enabled": True},
            }
        },
        flags={},
    )
    ctx.metrics["jobs_with_company_key"] = 1
    ctx.metrics["jobs_without_company_key"] = 0

    service = RunReadinessService(ctx)
    report = service.build_report(
        jobs=[{"title": "Backend Engineer"}],
        companies=[
            {
                "company_key": "cmp_email_only",
                "company_type_ai": "end_client",
                "opportunity_score": 70,
                "domain_validation_status": "rejected",
                "resolved_domain": "",
                "linkedin_company_url": "",
                "enrichment_source": "",
                "best_contact_email": "cto@emailonly.com",
            }
        ],
        leads=[{"company_key": "cmp_email_only", "email": "cto@emailonly.com"}],
    )

    assert report["icp_reachability_summary"]["strong_icp_companies"] == 1
    assert report["icp_reachability_summary"]["strong_icp_without_reachability"] == 0
