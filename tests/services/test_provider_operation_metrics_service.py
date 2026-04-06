from oie.orchestration.run_context import RunContext
from oie.services.provider_operation_metrics_service import ProviderOperationMetricsService


def test_provider_operation_metrics_service_builds_grouped_rows():
    ctx = RunContext.create(config={}, flags={})
    ctx.metrics.update(
        {
            "openai_classify_company_max_calls": 100,
            "openai_classify_company_used_calls": 5,
            "openai_classify_company_remaining_calls": 95,
            "openai_classify_company_started": 5,
            "openai_classify_company_success": 4,
            "openai_classify_company_retry_count": 1,
            "openai_classify_company_blocked_budget": 0,
            "openai_classify_company_blocked_provider": 0,
            "openai_classify_company_errors_timeout": 0,
            "openai_classify_company_errors_rate_limit": 1,
            "openai_classify_company_errors_http_5xx": 0,
            "openai_classify_company_errors_execution_error": 2,
            "hunter_search_domain_contacts_used_calls": 3,
            "hunter_search_domain_contacts_started": 3,
            "hunter_search_domain_contacts_success": 3,
        }
    )

    service = ProviderOperationMetricsService(ctx)
    rows = service.build_rows()

    assert len(rows) == 2

    openai_row = next(
        row for row in rows
        if row["provider"] == "openai" and row["operation"] == "classify_company"
    )
    hunter_row = next(
        row for row in rows
        if row["provider"] == "hunter" and row["operation"] == "search_domain_contacts"
    )

    assert openai_row["max_calls"] == 100
    assert openai_row["used_calls"] == 5
    assert openai_row["remaining_calls"] == 95
    assert openai_row["started"] == 5
    assert openai_row["success"] == 4
    assert openai_row["retry_count"] == 1
    assert openai_row["errors_rate_limit"] == 1
    assert openai_row["errors_execution_error"] == 2

    assert hunter_row["used_calls"] == 3
    assert hunter_row["started"] == 3
    assert hunter_row["success"] == 3
    assert hunter_row["max_calls"] is None
    assert hunter_row["remaining_calls"] is None
    assert hunter_row["retry_count"] == 0

    assert ctx.metrics["provider_operation_metrics_rows"] == 2


def test_provider_operation_metrics_service_ignores_unparseable_keys():
    ctx = RunContext.create(config={}, flags={})
    ctx.metrics.update(
        {
            "jobs_after_dedupe": 10,
            "openai": 2,
            "openai_errors_rate_limit": 3,  # no operation segment, should be ignored
        }
    )

    service = ProviderOperationMetricsService(ctx)
    rows = service.build_rows()

    assert rows == []
    assert ctx.metrics["provider_operation_metrics_rows"] == 0
