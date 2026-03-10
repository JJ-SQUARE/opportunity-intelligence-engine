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
    assert len(report["warnings"]) >= 1
