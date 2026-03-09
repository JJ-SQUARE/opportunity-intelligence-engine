from __future__ import annotations

from typing import Any, Dict

from oie.orchestration.run_context import RunContext
from oie.providers.provider_registry import ProviderRegistry


DEFAULT_PROVIDER_LIMITS = {
    "serpapi": 100,
    "apollo": 100,
    "hunter": 100,
    "openai": 100,
}


class ProviderControlService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.registry = ProviderRegistry()

    def initialize(self) -> ProviderRegistry:
        provider_limits = (
            self.ctx.config.get("providers", {}).get("limits", {}) or {}
        )
        circuit_breaker_config = (
            self.ctx.config.get("providers", {}).get("circuit_breakers", {}) or {}
        )

        for provider_name, default_limit in DEFAULT_PROVIDER_LIMITS.items():
            max_calls = int(provider_limits.get(provider_name, default_limit))
            failure_threshold = int(
                circuit_breaker_config.get(provider_name, {}).get("failure_threshold", 3)
            )

            self.registry.register_budget(provider_name, max_calls=max_calls)
            self.registry.register_circuit_breaker(
                provider_name,
                failure_threshold=failure_threshold,
            )

            self.ctx.budgets[provider_name] = {
                "max_calls": max_calls,
                "used_calls": 0,
                "remaining_calls": max_calls,
            }

        self.ctx.provider_state["registry_initialized"] = True
        self.ctx.metrics["provider_registry_initialized"] = True
        return self.registry

    def sync_budget_metrics(self) -> None:
        for provider_name, budget in self.registry.budgets.items():
            self.ctx.budgets[provider_name] = {
                "max_calls": budget.max_calls,
                "used_calls": budget.used_calls,
                "remaining_calls": budget.remaining(),
            }

            self.ctx.metrics[f"{provider_name}_budget_max_calls"] = budget.max_calls
            self.ctx.metrics[f"{provider_name}_budget_used_calls"] = budget.used_calls
            self.ctx.metrics[f"{provider_name}_budget_remaining_calls"] = budget.remaining()

    def consume_budget(self, provider_name: str, amount: int = 1) -> None:
        budget = self.registry.get_budget(provider_name)
        if budget is None:
            raise ValueError(f"No budget registered for provider={provider_name}")

        budget.consume(amount)
        self.sync_budget_metrics()

    def register_provider_success(self, provider_name: str) -> None:
        breaker = self.registry.get_circuit_breaker(provider_name)
        if breaker is not None:
            breaker.record_success()

        self.ctx.metrics[f"{provider_name}_success_count"] = (
            int(self.ctx.metrics.get(f"{provider_name}_success_count", 0)) + 1
        )

    def register_provider_failure(self, provider_name: str, error_type: str) -> None:
        breaker = self.registry.get_circuit_breaker(provider_name)
        if breaker is not None:
            breaker.record_failure()
            self.ctx.provider_state[f"{provider_name}_circuit_open"] = breaker.is_open

        metric_key = f"{provider_name}_errors_{error_type}"
        self.ctx.metrics[metric_key] = int(self.ctx.metrics.get(metric_key, 0)) + 1

    def can_execute(self, provider_name: str) -> bool:
        breaker = self.registry.get_circuit_breaker(provider_name)
        if breaker is not None and not breaker.can_execute():
            return False

        budget = self.registry.get_budget(provider_name)
        if budget is not None and not budget.allow():
            return False

        return True
