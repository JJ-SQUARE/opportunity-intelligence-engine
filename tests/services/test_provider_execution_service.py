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


def test_execute_records_operation_specific_success_metrics():
    ctx = RunContext.create(config={})
    pcs = ProviderControlService(ctx)
    pcs.initialize()

    service = ProviderExecutionService(ctx, pcs)

    def _ok(payload):
        return {"ok": True, "payload": payload}

    result = service.execute(
        "openai",
        "domain_ai_validation",
        _ok,
        {"company_name": "Tenaris"},
        cost=1,
    )

    assert result["ok"] is True
    assert ctx.metrics["openai_domain_ai_validation_started"] == 1
    assert ctx.metrics["openai_domain_ai_validation_success"] == 1


def test_execute_records_operation_specific_retry_and_error_metrics():
    ctx = RunContext.create(config={})
    pcs = ProviderControlService(ctx)
    pcs.initialize()

    service = ProviderExecutionService(ctx, pcs)

    attempts = {"n": 0}

    def _fail(*args, **kwargs):
        attempts["n"] += 1
        raise RuntimeError("boom")

    try:
        service.execute(
            "openai",
            "classify_company",
            _fail,
            {"company_name": "Acme"},
            cost=1,
        )
    except ProviderExecutionError:
        pass

    assert attempts["n"] >= 1
    assert ctx.metrics["openai_classify_company_started"] >= 1
    assert ctx.metrics["openai_classify_company_errors_execution_error"] >= 1
    assert ctx.metrics.get("openai_classify_company_retry_count", 0) >= 0


def test_execute_records_operation_specific_success_metrics():
    ctx = RunContext.create(config={})
    provider_control_service = ProviderControlService(ctx)
    provider_control_service.initialize()

    service = ProviderExecutionService(ctx, provider_control_service)

    def _ok(payload):
        return {"ok": True, "payload": payload}

    result = service.execute(
        "openai",
        "domain_ai_validation",
        _ok,
        {"company_name": "Tenaris"},
        cost=1,
    )

    assert result["ok"] is True
    assert ctx.metrics["openai_domain_ai_validation_started"] == 1
    assert ctx.metrics["openai_domain_ai_validation_success"] == 1


def test_execute_records_operation_specific_execution_error_metrics():
    ctx = RunContext.create(config={})
    provider_control_service = ProviderControlService(ctx)
    provider_control_service.initialize()

    service = ProviderExecutionService(ctx, provider_control_service)

    attempts = {"n": 0}

    def _fail(*args, **kwargs):
        attempts["n"] += 1
        raise RuntimeError("boom")

    try:
        service.execute(
            "openai",
            "classify_company",
            _fail,
            {"company_name": "Acme"},
            cost=1,
        )
    except ProviderExecutionError:
        pass

    assert attempts["n"] >= 1
    assert ctx.metrics["openai_classify_company_started"] >= 1
    assert ctx.metrics["openai_classify_company_errors_execution_error"] >= 1


def test_execute_respects_operation_specific_budget_limit():
    ctx = RunContext.create(
        config={
            "providers": {
                "operation_limits": {
                    "openai": {
                        "domain_ai_validation": 1,
                    }
                }
            }
        }
    )
    provider_control_service = ProviderControlService(ctx)
    provider_control_service.initialize()

    service = ProviderExecutionService(ctx, provider_control_service)

    def _ok(payload):
        return {"ok": True}

    result = service.execute(
        "openai",
        "domain_ai_validation",
        _ok,
        {"company_name": "Tenaris"},
        cost=1,
    )
    assert result["ok"] is True

    try:
        service.execute(
            "openai",
            "domain_ai_validation",
            _ok,
            {"company_name": "Sofka"},
            cost=1,
        )
        assert False, "Expected ProviderExecutionBlockedError"
    except ProviderExecutionBlockedError:
        pass

    assert ctx.metrics["openai_domain_ai_validation_used_calls"] == 1
    assert ctx.metrics["openai_domain_ai_validation_max_calls"] == 1
    assert ctx.metrics["openai_domain_ai_validation_remaining_calls"] == 0
    assert ctx.metrics["openai_domain_ai_validation_blocked_budget"] == 1


def test_execute_allows_other_operation_when_one_operation_budget_is_exhausted():
    ctx = RunContext.create(
        config={
            "providers": {
                "operation_limits": {
                    "openai": {
                        "domain_ai_validation": 1,
                        "classify_company": 2,
                    }
                }
            }
        }
    )
    provider_control_service = ProviderControlService(ctx)
    provider_control_service.initialize()

    service = ProviderExecutionService(ctx, provider_control_service)

    def _ok(payload):
        return {"ok": True}

    service.execute(
        "openai",
        "domain_ai_validation",
        _ok,
        {"company_name": "Tenaris"},
        cost=1,
    )

    try:
        service.execute(
            "openai",
            "domain_ai_validation",
            _ok,
            {"company_name": "Sofka"},
            cost=1,
        )
    except ProviderExecutionBlockedError:
        pass

    result = service.execute(
        "openai",
        "classify_company",
        _ok,
        {"company_name": "Acme"},
        cost=1,
    )

    assert result["ok"] is True
    assert ctx.metrics["openai_classify_company_used_calls"] == 1
    assert ctx.metrics["openai_classify_company_remaining_calls"] == 1

def test_provider_execution_service_records_status_code_in_http_error_event():
    import requests

    ctx = RunContext.create(
        config={
            "providers": {
                "limits": {"serpapi": 3},
                "retry_policy": {
                    "serpapi": {
                        "max_attempts": 1,
                        "base_delay_seconds": 0.0,
                        "backoff_multiplier": 1.0,
                    }
                },
            }
        }
    )
    provider_control_service = ProviderControlService(ctx)
    provider_control_service.initialize()

    service = ProviderExecutionService(ctx, provider_control_service)

    class _FakeResponse:
        status_code = 429

    def _fail():
        raise requests.exceptions.HTTPError("429 Too Many Requests", response=_FakeResponse())

    try:
        service.execute("serpapi", "search_google", _fail, cost=1)
        assert False, "Expected ProviderExecutionError"
    except ProviderExecutionError:
        pass

    rate_limit_events = [
        event for event in ctx.provider_events
        if event.get("provider") == "serpapi" and event.get("event_type") == "rate_limit"
    ]

    assert rate_limit_events
    assert rate_limit_events[0]["status_code"] == 429

def test_provider_execution_service_blocks_only_failing_operation_on_auth_error():
    import requests

    ctx = RunContext.create(
        config={
            "providers": {
                "limits": {"apollo": 5},
                "retry_policy": {
                    "apollo": {
                        "max_attempts": 3,
                        "base_delay_seconds": 0.0,
                        "backoff_multiplier": 1.0,
                    }
                },
            }
        }
    )
    provider_control_service = ProviderControlService(ctx)
    provider_control_service.initialize()

    service = ProviderExecutionService(ctx, provider_control_service)

    class _FakeResponse:
        status_code = 401

    attempts = {"auth_fail": 0, "other_ok": 0}

    def _auth_fail():
        attempts["auth_fail"] += 1
        raise requests.exceptions.HTTPError(
            "401 Client Error: Unauthorized",
            response=_FakeResponse(),
        )

    def _other_ok():
        attempts["other_ok"] += 1
        return {"ok": True}

    try:
        service.execute("apollo", "enrich_company_by_domain", _auth_fail, cost=1)
        assert False, "Expected ProviderExecutionError"
    except ProviderExecutionError:
        pass

    assert attempts["auth_fail"] == 1
    assert ctx.metrics["apollo_enrich_company_by_domain_errors_auth"] == 1
    assert ctx.metrics.get("apollo_enrich_company_by_domain_retry_count", 0) == 0
    assert ctx.metrics.get("apollo_errors_execution_error", 0) == 0
    assert ctx.provider_state.get("apollo_circuit_open") is not True

    result = service.execute("apollo", "search_people_by_domain_and_titles", _other_ok, cost=1)

    assert result["ok"] is True
    assert attempts["other_ok"] == 1
    assert ctx.metrics["apollo_search_people_by_domain_and_titles_success"] == 1


def test_provider_execution_service_records_permission_metric_on_403():
    import requests

    ctx = RunContext.create(
        config={
            "providers": {
                "limits": {"apollo": 5},
                "retry_policy": {
                    "apollo": {
                        "max_attempts": 3,
                        "base_delay_seconds": 0.0,
                        "backoff_multiplier": 1.0,
                    }
                },
            }
        }
    )
    provider_control_service = ProviderControlService(ctx)
    provider_control_service.initialize()

    service = ProviderExecutionService(ctx, provider_control_service)

    class _FakeResponse:
        status_code = 403

    attempts = {"n": 0}

    def _forbidden():
        attempts["n"] += 1
        raise requests.exceptions.HTTPError(
            "403 Client Error: Forbidden",
            response=_FakeResponse(),
        )

    try:
        service.execute("apollo", "enrich_company_by_domain", _forbidden, cost=1)
        assert False, "Expected ProviderExecutionError"
    except ProviderExecutionError:
        pass

    assert attempts["n"] == 1
    assert ctx.metrics["apollo_enrich_company_by_domain_errors_auth"] == 1
    assert ctx.metrics["apollo_enrich_company_by_domain_errors_permission"] == 1
    assert ctx.metrics.get("apollo_enrich_company_by_domain_retry_count", 0) == 0
