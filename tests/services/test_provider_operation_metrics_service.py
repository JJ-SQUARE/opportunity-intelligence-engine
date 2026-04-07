from oie.orchestration.run_context import RunContext
from oie.services.provider_operation_metrics_service import ProviderOperationMetricsService


def test_provider_operation_metrics_service_builds_rows_and_normalizes_values():
    ctx = RunContext.create(config={}, flags={})
    ctx.metrics.update(
        {
            "openai_classify_company_max_calls": "3",
            "openai_classify_company_used_calls": "2",
            "openai_classify_company_remaining_calls": "1",
            "openai_classify_company_started": "2",
            "openai_classify_company_success": "1",
            "openai_classify_company_retry_count": "1",
            "openai_classify_company_blocked_budget": "0",
            "openai_classify_company_blocked_provider": "0",
            "openai_classify_company_errors_timeout": "0",
            "openai_classify_company_errors_rate_limit": "0",
            "openai_classify_company_errors_http_5xx": "0",
            "openai_classify_company_errors_execution_error": "1",
        }
    )

    service = ProviderOperationMetricsService(ctx)
    rows = service.build_rows()

    assert len(rows) == 1
    row = rows[0]

    assert row["provider"] == "openai"
    assert row["operation"] == "classify_company"
    assert row["max_calls"] == 3
    assert row["used_calls"] == 2
    assert row["remaining_calls"] == 1
    assert row["started"] == 2
    assert row["success"] == 1
    assert row["retry_count"] == 1
    assert row["errors_execution_error"] == 1
    assert ctx.metrics["provider_operation_metrics_rows"] == 1


def test_provider_operation_metrics_service_ignores_unrelated_metrics():
    ctx = RunContext.create(config={}, flags={})
    ctx.metrics.update(
        {
            "jobs_after_dedupe": 10,
            "openai_budget_used_calls": 3,
            "random_metric": "abc",
        }
    )

    service = ProviderOperationMetricsService(ctx)
    rows = service.build_rows()

    assert rows == []
    assert ctx.metrics["provider_operation_metrics_rows"] == 0
