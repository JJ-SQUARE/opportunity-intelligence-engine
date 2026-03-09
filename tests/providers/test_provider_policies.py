from oie.providers.policies.budget_guard import BudgetExceededError, BudgetGuard
from oie.providers.policies.circuit_breaker import CircuitBreaker


def test_budget_guard_consumes_until_limit():
    guard = BudgetGuard(provider="openai", max_calls=2)

    guard.consume()
    guard.consume()

    assert guard.used_calls == 2
    assert guard.remaining() == 0


def test_budget_guard_raises_when_exceeded():
    guard = BudgetGuard(provider="openai", max_calls=1)

    guard.consume()

    try:
        guard.consume()
        assert False, "Expected BudgetExceededError"
    except BudgetExceededError:
        assert True


def test_circuit_breaker_opens_after_threshold():
    breaker = CircuitBreaker(provider="apollo", failure_threshold=2)

    assert breaker.can_execute() is True

    breaker.record_failure()
    assert breaker.can_execute() is True

    breaker.record_failure()
    assert breaker.can_execute() is False
