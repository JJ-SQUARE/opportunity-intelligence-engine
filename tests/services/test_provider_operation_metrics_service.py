from oie.orchestration.run_context import RunContext
from oie.services.provider_operation_metrics_service import ProviderOperationMetricsService


def test_provider_operation_metrics_service_builds_rows():
    ctx = RunContext.create(config={})
    ctx.metrics.update(
        {
            "openai_classify_company_max_calls": 80,
            "openai_classify_company_used_calls": 12,
            "openai_classify_company_remaining_calls": 68,
            "openai_classify_company_started": 12,
            "openai_classify_company_success": 10,
            "openai_classify_company_retry_count": 2,
            "openai_classify_company_errors_execution_error": 2,
            "openai_domain_ai_validation_max_calls": 20,
            "openai_domain_ai_validation_used_calls": 5,
            "openai_domain_ai_validation_remaining_calls": 15,
            "openai_domain_ai_validation_started": 5,
            "openai_domain_ai_validation_success": 5,
            "serpapi_search_google_max_calls": 25,
            "serpapi_search_google_used_calls": 7,
            "serpapi_search_google_remaining_calls": 18,
            "serpapi_search_google_started": 7,
            "serpapi_search_google_success": 7,
        }
    )

    service = ProviderOperationMetricsService(ctx)
    rows = service.build_rows()

    assert len(rows) == 3

    by_key = {(r["provider"], r["operation"]): r for r in rows}

    assert by_key[("openai", "classify_company")]["used_calls"] == 12
    assert by_key[("openai", "classify_company")]["errors_execution_error"] == 2
    assert by_key[("openai", "domain_ai_validation")]["success"] == 5
    assert by_key[("serpapi", "search_google")]["remaining_calls"] == 18
