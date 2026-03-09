from __future__ import annotations

from typing import Any, Dict

from oie.providers.policies.budget_guard import BudgetGuard
from oie.providers.policies.circuit_breaker import CircuitBreaker


class ProviderRegistry:
    def __init__(self) -> None:
        self.clients: Dict[str, Any] = {}
        self.budgets: Dict[str, BudgetGuard] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

    def register_client(self, provider_name: str, client: Any) -> None:
        self.clients[provider_name] = client

    def register_budget(self, provider_name: str, max_calls: int) -> None:
        self.budgets[provider_name] = BudgetGuard(provider=provider_name, max_calls=max_calls)

    def register_circuit_breaker(self, provider_name: str, failure_threshold: int = 3) -> None:
        self.circuit_breakers[provider_name] = CircuitBreaker(
            provider=provider_name,
            failure_threshold=failure_threshold,
        )

    def get_client(self, provider_name: str) -> Any:
        return self.clients.get(provider_name)

    def get_budget(self, provider_name: str) -> BudgetGuard | None:
        return self.budgets.get(provider_name)

    def get_circuit_breaker(self, provider_name: str) -> CircuitBreaker | None:
        return self.circuit_breakers.get(provider_name)
