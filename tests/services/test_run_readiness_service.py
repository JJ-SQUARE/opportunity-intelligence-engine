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

    service = RunReadinessService(ctx)

    report = service.build_report(
        jobs=[{"title": "Backend Engineer"}],
        companies=[{"company_key": "cmp_a"}],
        leads=[],
    )

    assert report["is_ready_for_review"] is True
    assert "google_jobs" in report["enabled_collectors"]
    assert report["jobs_count"] == 1
    assert report["companies_count"] == 1
    assert report["leads_count"] == 0
    assert report["jobs_without_company_key"] == 1
    assert "run_metrics_summary_json" in report["outputs"]
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

