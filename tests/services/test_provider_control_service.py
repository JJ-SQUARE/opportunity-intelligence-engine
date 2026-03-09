from oie.orchestration.run_context import RunContext
from oie.services.provider_control_service import ProviderControlService


def test_provider_control_service_initializes_budgets():
    ctx = RunContext.create(
        config={
            "providers": {
                "limits": {
                    "serpapi": 10,
                    "apollo": 5,
                }
            }
        }
    )
    service = ProviderControlService(ctx)

    registry = service.initialize()

    assert registry.get_budget("serpapi") is not None
    assert registry.get_budget("serpapi").max_calls == 10
    assert registry.get_budget("apollo").max_calls == 5
    assert ctx.metrics["provider_registry_initialized"] is True


def test_provider_control_service_consumes_budget():
    ctx = RunContext.create(config={})
    service = ProviderControlService(ctx)
    service.initialize()

    service.consume_budget("openai", amount=2)

    assert ctx.budgets["openai"]["used_calls"] == 2
    assert ctx.budgets["openai"]["remaining_calls"] == 98


def test_provider_control_service_tracks_failures_and_opens_circuit():
    ctx = RunContext.create(
        config={
            "providers": {
                "circuit_breakers": {
                    "hunter": {
                        "failure_threshold": 2
                    }
                }
            }
        }
    )
    service = ProviderControlService(ctx)
    service.initialize()

    assert service.can_execute("hunter") is True

    service.register_provider_failure("hunter", "timeout")
    assert service.can_execute("hunter") is True

    service.register_provider_failure("hunter", "timeout")
    assert service.can_execute("hunter") is False
    assert ctx.provider_state["hunter_circuit_open"] is True
    assert ctx.metrics["hunter_errors_timeout"] == 2
