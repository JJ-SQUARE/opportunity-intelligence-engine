from oie.orchestration.run_context import RunContext
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import (
    ProviderExecutionBlockedError,
    ProviderExecutionError,
    ProviderExecutionService,
)


def test_provider_execution_service_consumes_budget_and_records_success():
    ctx = RunContext.create(config={"providers": {"limits": {"openai": 3}}})
    control = ProviderControlService(ctx)
    control.initialize()

    service = ProviderExecutionService(ctx, control)

    result = service.execute("openai", "dummy_call", lambda: {"ok": True}, cost=1)

    assert result == {"ok": True}
    assert ctx.budgets["openai"]["used_calls"] == 1
    assert ctx.metrics["openai_success_count"] == 1
    assert len(ctx.provider_events) >= 2


def test_provider_execution_service_records_failure_after_retries():
    ctx = RunContext.create(
        config={
            "providers": {
                "limits": {"openai": 3},
                "retry_policy": {
                    "openai": {
                        "max_attempts": 2,
                        "base_delay_seconds": 0.0,
                        "backoff_multiplier": 1.0,
                    }
                },
            }
        }
    )
    control = ProviderControlService(ctx)
    control.initialize()

    service = ProviderExecutionService(ctx, control)

    def failing_call():
        raise ValueError("boom")

    try:
        service.execute("openai", "dummy_fail", failing_call, cost=1)
        assert False, "Expected ProviderExecutionError"
    except ProviderExecutionError:
        assert True

    assert ctx.metrics["openai_errors_execution_error"] == 2
    assert ctx.metrics["openai_retry_count"] == 1


def test_provider_execution_service_respects_dry_run_mode():
    ctx = RunContext.create(
        config={"providers": {"limits": {"openai": 3}}},
        flags={"dry_run": True},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    service = ProviderExecutionService(ctx, control)

    try:
        service.execute("openai", "dummy_call", lambda: {"ok": True}, cost=1)
        assert False, "Expected ProviderExecutionBlockedError"
    except ProviderExecutionBlockedError:
        assert True

    assert ctx.budgets["openai"]["used_calls"] == 0
