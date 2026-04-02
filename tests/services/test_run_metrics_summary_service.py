from oie.orchestration.run_context import RunContext
from oie.services.run_metrics_summary_service import RunMetricsSummaryService


def test_run_metrics_summary_service_builds_summary():
    ctx = RunContext.create(config={}, flags={})
    ctx.metrics.update(
        {
            "jobs_collected_raw": 120,
            "jobs_after_dedupe": 95,
            "jobs_deduplicated": 25,
            "master_jobs_duplicates_detected": 10,
            "master_jobs_unique_to_append": 85,
            "companies_detected": 40,
            "companies_after_identity_dedupe": 38,
            "companies_with_domain": 20,
            "companies_enriched": 12,
            "companies_classified": 38,
            "companies_scored": 38,
            "leads_generated": 18,
            "leads_ranked": 18,
            "best_leads_selected": 15,
            "domain_resolution_accepted": 20,
            "domain_resolution_review": 8,
            "domain_resolution_rejected": 12,
            "domain_review_queue_count": 8,
            "run_readiness_ready": True,
            "run_readiness_warnings": 2,
            "openai_errors_execution_error": 3,
            "serpapi_search_google_errors_rate_limit": 2,
            "openai_classify_company_blocked_budget": 4,
            "hunter_search_domain_contacts_blocked_provider": 6,
        }
    )
    ctx.provider_events.extend(
        [
            {"provider": "openai", "event_type": "execution_error", "message": "x", "metadata": {}},
            {"provider": "serpapi", "event_type": "rate_limit", "message": "y", "metadata": {}},
        ]
    )

    service = RunMetricsSummaryService(ctx)
    summary = service.build_summary()

    assert summary["jobs_collected"] == 120
    assert summary["jobs_after_dedupe"] == 95
    assert summary["companies_detected"] == 40
    assert summary["companies_with_domain"] == 20
    assert summary["leads_generated"] == 18
    assert summary["provider_events_count"] == 2
    assert summary["provider_errors"]["openai"]["execution_error"] == 3
    assert summary["provider_errors"]["serpapi"]["rate_limit"] == 2
    assert summary["provider_blocks"]["openai"]["blocked_budget"] == 4
    assert summary["provider_blocks"]["hunter"]["blocked_provider"] == 6
