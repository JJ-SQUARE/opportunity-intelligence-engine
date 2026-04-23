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
            "master_leads_duplicates_detected": 4,
            "master_leads_unique_to_append": 14,
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
            "master_schema_errors_count": 2,
            "master_jobs_rows_written": 85,
            "master_companies_rows_written": 38,
            "master_leads_rows_written": 14,
            "master_jobs_write_succeeded": True,
            "master_companies_write_succeeded": True,
            "master_leads_write_succeeded": False,
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
    assert summary["leads_duplicates_detected"] == 4
    assert summary["leads_unique_to_append"] == 14
    assert summary["provider_events_count"] == 2
    assert summary["provider_errors"]["openai"]["execution_error"] == 3
    assert summary["provider_errors"]["serpapi"]["rate_limit"] == 2
    assert summary["provider_blocks"]["openai"]["blocked_budget"] == 4
    assert summary["provider_blocks"]["hunter"]["blocked_provider"] == 6

    assert summary["master_data"]["schema_errors_count"] == 2
    assert summary["master_data"]["jobs_rows_written"] == 85
    assert summary["master_data"]["companies_rows_written"] == 38
    assert summary["master_data"]["leads_rows_written"] == 14
    assert summary["master_data"]["jobs_write_succeeded"] is True
    assert summary["master_data"]["leads_write_succeeded"] is False
    assert summary["counts_original"]["jobs_duplicates_detected_master"] == 10
    assert summary["counts_original"]["leads_duplicates_detected_master"] == 4
    assert summary["counts_effective"]["jobs"] == 85
    assert summary["counts_effective"]["companies"] == 38
    assert summary["counts_effective"]["leads"] == 14
    assert summary["counts_quality"]["jobs_effective_lt_original"] is True
    assert summary["counts_quality"]["companies_effective_lte_detected"] is True
    assert summary["counts_quality"]["leads_effective_lte_selected"] is True

def test_run_metrics_summary_service_builds_count_deltas():
    ctx = RunContext.create(config={}, flags={})
    ctx.metrics.update(
        {
            "jobs_after_dedupe": 100,
            "master_jobs_unique_to_append": 80,
            "companies_detected": 40,
            "companies_after_identity_dedupe": 35,
            "best_leads_selected": 20,
            "master_leads_unique_to_append": 14,
        }
    )

    summary = RunMetricsSummaryService(ctx).build_summary()

    assert summary["count_deltas"]["jobs_removed_by_master_dedup"] == 20
    assert summary["count_deltas"]["companies_removed_after_identity"] == 5
    assert summary["count_deltas"]["leads_removed_by_master_dedup"] == 6
    assert summary["counts_quality"]["jobs_effective_lt_original"] is True
    assert summary["counts_quality"]["companies_effective_lte_detected"] is True
    assert summary["counts_quality"]["leads_effective_lte_selected"] is True



def test_run_metrics_summary_service_includes_persistence_and_master_quality_details():
    ctx = RunContext.create(config={}, flags={})
    ctx.metrics.update(
        {
            "jobs_after_dedupe": 8,
            "master_jobs_unique_to_append": 5,
            "companies_detected": 4,
            "companies_after_identity_dedupe": 3,
            "best_leads_selected": 3,
            "master_leads_unique_to_append": 2,
            "master_jobs_rows_written": 5,
            "master_companies_rows_written": 3,
            "master_leads_rows_written": 2,
            "master_jobs_write_attempted": 5,
            "master_companies_write_attempted": 3,
            "master_leads_write_attempted": 2,
            "master_jobs_write_errors_count": 0,
            "master_companies_write_errors_count": 1,
            "master_leads_write_errors_count": 0,
            "persistence_errors_count": 2,
            "persistence_schema_errors_count": 1,
            "persistence_sqlite_operational_errors_count": 1,
            "persistence_initialize_succeeded": True,
            "persistence_run_succeeded": True,
            "persistence_metrics_succeeded": True,
            "persistence_provider_events_succeeded": True,
            "persistence_provider_operation_metrics_succeeded": True,
            "persistence_companies_succeeded": False,
            "persistence_jobs_succeeded": True,
            "persistence_leads_succeeded": True,
        }
    )

    summary = RunMetricsSummaryService(ctx).build_summary()

    assert summary["master_data"]["jobs_write_attempted"] == 5
    assert summary["master_data"]["companies_write_attempted"] == 3
    assert summary["master_data"]["leads_write_attempted"] == 2
    assert summary["master_data"]["companies_write_errors_count"] == 1
    assert summary["persistence_data"]["errors_count"] == 2
    assert summary["persistence_data"]["schema_errors_count"] == 1
    assert summary["persistence_data"]["sqlite_operational_errors_count"] == 1
    assert summary["persistence_data"]["companies_succeeded"] is False
    assert summary["counts_quality"]["master_jobs_rows_match_effective"] is True
    assert summary["counts_quality"]["master_companies_rows_match_effective"] is True
    assert summary["counts_quality"]["master_leads_rows_match_effective"] is True

def test_run_metrics_summary_service_persists_original_and_effective_counts_to_provider_state():
    ctx = RunContext.create(config={}, flags={})
    ctx.metrics.update(
        {
            "jobs_after_dedupe": 12,
            "master_jobs_unique_to_append": 9,
            "companies_detected": 5,
            "companies_after_identity_dedupe": 4,
            "best_leads_selected": 3,
            "master_leads_unique_to_append": 2,
        }
    )

    summary = RunMetricsSummaryService(ctx).build_summary()

    assert summary["counts_original"]["jobs_after_dedupe"] == 12
    assert summary["counts_effective"]["jobs"] == 9
    assert ctx.provider_state["run_metrics_summary_counts_original"]["jobs_after_dedupe"] == 12
    assert ctx.provider_state["run_metrics_summary_counts_effective"]["jobs"] == 9
    assert ctx.provider_state["run_metrics_summary_counts"]["jobs_count"] == 9
    assert ctx.provider_state["run_metrics_summary_counts"]["companies_count"] == 4
    assert ctx.provider_state["run_metrics_summary_counts"]["leads_count"] == 2

