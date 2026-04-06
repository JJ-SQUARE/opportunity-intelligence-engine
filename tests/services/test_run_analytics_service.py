from oie.orchestration.run_context import RunContext
from oie.services.run_analytics_service import RunAnalyticsService


def test_run_analytics_service_builds_consolidated_payload():
    ctx = RunContext.create(config={}, flags={})
    ctx.metrics["jobs_with_company_key"] = 2
    ctx.metrics["jobs_without_company_key"] = 1
    ctx.metrics["domain_review_queue_count"] = 3

    service = RunAnalyticsService(ctx)

    analytics = service.build_analytics(
        status="company_pipeline_completed",
        jobs=[
            {"source": "google_jobs"},
            {"source": "linkedin_serpapi"},
            {"source": "google_jobs"},
        ],
        companies=[
            {
                "company_key": "cmp_a",
                "company_display": "Acme Inc.",
                "resolved_domain": "acme.com",
                "company_type_ai": "end_client",
                "opportunity_score": 42,
                "total_openings": 3,
                "remote_jobs": 2,
                "contractor_jobs": 1,
            },
            {
                "company_key": "cmp_b",
                "company_display": "Beta Inc.",
                "resolved_domain": "beta.com",
                "company_type_ai": "consulting",
                "opportunity_score": 20,
                "total_openings": 1,
                "remote_jobs": 1,
                "contractor_jobs": 0,
            },
        ],
        leads=[
            {"company_key": "cmp_a"},
            {"company_key": "cmp_b"},
        ],
        duplicate_jobs=[
            {"source": "google_jobs"},
        ],
        collector_metrics=[
            {"source": "google_jobs", "jobs_collected": 2},
            {"source": "linkedin_serpapi", "jobs_collected": 1},
        ],
        collector_contribution=[
            {"source": "google_jobs", "contribution_score": 7.0},
            {"source": "linkedin_serpapi", "contribution_score": 5.0},
        ],
        collector_roi=[
            {"source": "google_jobs", "utility_score": 6.5},
            {"source": "linkedin_serpapi", "utility_score": 4.0},
        ],
        provider_operation_metrics=[
            {"provider": "openai", "operation": "classify_company", "used_calls": 2},
        ],
        readiness_report={
            "is_ready_for_review": True,
            "warnings": ["warn a"],
        },
        run_metrics_summary={
            "run_readiness_ready": True,
            "run_readiness_warnings": 1,
            "provider_errors": {"openai": {"execution_error": 1}},
            "provider_blocks": {"hunter": {"blocked_provider": 2}},
        },
        executive_summary={
            "companies_count": 2,
            "top_companies": [{"company_display": "Acme Inc."}],
        },
    )

    assert analytics["status"] == "company_pipeline_completed"
    assert analytics["counts"]["jobs"] == 3
    assert analytics["counts"]["companies"] == 2
    assert analytics["counts"]["leads"] == 2
    assert analytics["counts"]["duplicate_jobs"] == 1

    assert analytics["quality"]["jobs_with_company_key"] == 2
    assert analytics["quality"]["jobs_without_company_key"] == 1
    assert analytics["quality"]["domain_review_queue_count"] == 3

    assert analytics["top_collectors"]["by_jobs"][0]["source"] == "google_jobs"
    assert analytics["top_collectors"]["by_contribution"][0]["source"] == "google_jobs"
    assert analytics["top_collectors"]["by_roi"][0]["source"] == "google_jobs"

    assert analytics["top_companies"][0]["company_display"] == "Acme Inc."
    assert analytics["provider_health"]["provider_errors"]["openai"]["execution_error"] == 1
    assert analytics["provider_health"]["provider_blocks"]["hunter"]["blocked_provider"] == 2
    assert analytics["provider_health"]["provider_operation_metrics"][0]["provider"] == "openai"

    assert analytics["readiness"]["is_ready_for_review"] is True
    assert analytics["executive_summary"]["companies_count"] == 2
    assert ctx.metrics["run_analytics_generated"] is True
