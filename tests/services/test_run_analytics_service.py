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
                "classification_confidence_ai": 0.95,
                "opportunity_score": 42,
                "score_openings": 16,
                "score_remote": 8,
                "score_contractor": 6,
                "score_multi_source": 10,
                "score_company_type": 2,
                "total_openings": 3,
                "remote_jobs": 2,
                "contractor_jobs": 1,
            },
            {
                "company_key": "cmp_b",
                "company_display": "Beta Inc.",
                "resolved_domain": "beta.com",
                "company_type_ai": "consulting",
                "classification_confidence_ai": 0.8,
                "opportunity_score": 20,
                "score_openings": 8,
                "score_remote": 4,
                "score_contractor": 0,
                "score_multi_source": 0,
                "score_company_type": 10,
                "total_openings": 1,
                "remote_jobs": 1,
                "contractor_jobs": 0,
            },
        ],
        leads=[
            {
                "company_key": "cmp_a",
                "contact_name": "Jane Doe",
                "contact_title": "CTO",
                "email": "jane@acme.com",
                "linkedin_url": "https://linkedin.com/in/jane",
                "lead_source": "apollo_people",
                "lead_confidence": 0.9,
                "email_quality_score": 95,
                "lead_capture_reason": "apollo_match | title:CTO | email_quality:95",
                "lead_relevance_score": 197,
                "lead_score_title": 100,
                "lead_score_source": 30,
                "lead_score_email": 20,
                "lead_score_linkedin": 10,
                "lead_score_email_quality": 19,
                "lead_score_confidence": 18,
            },
            {
                "company_key": "cmp_b",
                "contact_name": "John Roe",
                "contact_title": "VP Engineering",
                "email": "john@beta.com",
                "linkedin_url": "",
                "lead_source": "hunter_domain_search",
                "lead_confidence": 0.5,
                "email_quality_score": 70,
                "lead_capture_reason": "hunter_match | title:VP Engineering | email_quality:70",
                "lead_relevance_score": 139,
                "lead_score_title": 90,
                "lead_score_source": 15,
                "lead_score_email": 20,
                "lead_score_linkedin": 0,
                "lead_score_email_quality": 14,
                "lead_score_confidence": 10,
            },
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
            "master_data": {
                "schema_errors_count": 1,
                "jobs_rows_written": 2,
                "companies_rows_written": 2,
                "leads_rows_written": 2,
            },
            "persistence_data": {
                "errors_count": 1,
                "schema_errors_count": 1,
                "sqlite_operational_errors_count": 1,
                "companies_succeeded": False,
            },
            "counts_original": {
                "jobs_collected_raw": 5,
                "jobs_after_dedupe": 3,
                "jobs_duplicates_detected_master": 1,
                "jobs_unique_to_append_master": 2,
                "companies_detected": 3,
                "companies_after_identity_dedupe": 2,
                "leads_generated": 4,
                "best_leads_selected": 3,
                "leads_duplicates_detected_master": 1,
                "leads_unique_to_append_master": 2,
            },
            "counts_effective": {
                "jobs": 2,
                "companies": 2,
                "leads": 2,
            },
            "counts_quality": {
                "jobs_effective_lt_original": True,
                "companies_effective_lte_detected": True,
                "leads_effective_lte_selected": True,
            },
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
    assert analytics["quality"]["provider_events_count"] == 0

    assert analytics["top_collectors"]["by_jobs"][0]["source"] == "google_jobs"
    assert analytics["top_collectors"]["by_contribution"][0]["source"] == "google_jobs"
    assert analytics["top_collectors"]["by_roi"][0]["source"] == "google_jobs"

    assert analytics["top_companies"][0]["company_display"] == "Acme Inc."
    assert analytics["top_companies"][0]["classification_confidence_ai"] == 0.95
    assert analytics["top_companies"][0]["score_openings"] == 16

    assert analytics["top_leads"][0]["contact_name"] == "Jane Doe"
    assert analytics["top_leads"][0]["lead_relevance_score"] == 197
    assert analytics["top_leads"][0]["lead_score_title"] == 100
    assert analytics["top_leads"][0]["email_quality_score"] == 95
    assert "apollo_match" in analytics["top_leads"][0]["lead_capture_reason"]

    assert analytics["provider_health"]["provider_errors"]["openai"]["execution_error"] == 1
    assert analytics["provider_health"]["provider_blocks"]["hunter"]["blocked_provider"] == 2
    assert analytics["provider_health"]["provider_operation_metrics"][0]["provider"] == "openai"
    assert analytics["persistence_data"]["errors_count"] == 1
    assert analytics["persistence_data"]["companies_succeeded"] is False
    assert analytics["counts_quality"]["jobs_effective_lt_original"] is True
    assert analytics["counts_quality"]["companies_effective_lte_detected"] is True
    assert analytics["counts_quality"]["leads_effective_lte_selected"] is True

    assert analytics["readiness"]["is_ready_for_review"] is True
    assert analytics["executive_summary"]["companies_count"] == 2
    assert ctx.metrics["run_analytics_generated"] is True
    assert ctx.metrics["run_analytics_top_leads_count"] == 2


def test_run_analytics_service_prefers_higher_quality_lead_on_tie():
    ctx = RunContext.create(config={}, flags={})
    service = RunAnalyticsService(ctx)

    analytics = service.build_analytics(
        status="company_pipeline_completed",
        jobs=[],
        companies=[],
        leads=[
            {
                "company_key": "cmp_a",
                "contact_name": "Lower Quality",
                "contact_title": "VP Engineering",
                "email": "low@acme.com",
                "linkedin_url": "",
                "lead_source": "hunter_domain_search",
                "lead_confidence": 0.5,
                "email_quality_score": 60,
                "lead_capture_reason": "hunter_match | title:VP Engineering | email_quality:60",
                "lead_relevance_score": 139,
                "lead_score_title": 90,
                "lead_score_source": 15,
                "lead_score_email": 20,
                "lead_score_linkedin": 0,
                "lead_score_email_quality": 12,
                "lead_score_confidence": 10,
            },
            {
                "company_key": "cmp_a",
                "contact_name": "Higher Quality",
                "contact_title": "VP Engineering",
                "email": "high@acme.com",
                "linkedin_url": "",
                "lead_source": "hunter_domain_search",
                "lead_confidence": 0.5,
                "email_quality_score": 90,
                "lead_capture_reason": "hunter_match | title:VP Engineering | email_quality:90",
                "lead_relevance_score": 139,
                "lead_score_title": 90,
                "lead_score_source": 15,
                "lead_score_email": 20,
                "lead_score_linkedin": 0,
                "lead_score_email_quality": 18,
                "lead_score_confidence": 10,
            },
        ],
        duplicate_jobs=[],
        collector_metrics=[],
        collector_contribution=[],
        collector_roi=[],
        provider_operation_metrics=[],
        readiness_report={"is_ready_for_review": True, "warnings": []},
        run_metrics_summary={
            "run_readiness_ready": True,
            "run_readiness_warnings": 0,
            "provider_errors": {},
            "provider_blocks": {},
        },
        executive_summary={},
    )

    assert analytics["top_leads"][0]["contact_name"] == "Higher Quality"
    assert analytics["top_leads"][0]["email_quality_score"] == 90
    assert analytics["counts"]["jobs"] == 0
    assert analytics["counts"]["companies"] == 0
    assert analytics["counts"]["leads"] == 2

def test_run_analytics_service_exposes_non_negative_effective_deltas():
    ctx = RunContext.create(config={}, flags={})
    service = RunAnalyticsService(ctx)

    analytics = service.build_analytics(
        status="company_pipeline_completed",
        jobs=[],
        companies=[],
        leads=[],
        duplicate_jobs=[],
        collector_metrics=[],
        collector_contribution=[],
        collector_roi=[],
        provider_operation_metrics=[],
        readiness_report={"is_ready_for_review": True, "warnings": []},
        run_metrics_summary={
            "run_readiness_ready": True,
            "run_readiness_warnings": 0,
            "provider_errors": {},
            "provider_blocks": {},
            "counts_original": {
                "jobs_after_dedupe": 2,
                "best_leads_selected": 1,
            },
            "counts_effective": {
                "jobs": 5,
                "leads": 3,
            },
        },
        executive_summary={},
    )

    assert analytics["quality"]["effective_jobs_vs_original_delta"] == 0
    assert analytics["quality"]["effective_leads_vs_selected_delta"] == 0

