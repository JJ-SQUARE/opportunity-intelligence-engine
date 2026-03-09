from __future__ import annotations

import time
from typing import Any, Callable

from oie.orchestration.run_context import RunContext
from oie.providers.policies.budget_guard import BudgetExceededError
from oie.services.provider_control_service import ProviderControlService


class ProviderExecutionError(RuntimeError):
    pass


class ProviderExecutionBlockedError(ProviderExecutionError):
    pass


class ProviderExecutionService:
    def __init__(self, ctx: RunContext, provider_control_service: ProviderControlService) -> None:
        self.ctx = ctx
        self.provider_control_service = provider_control_service

    def execute(
        self,
        provider_name: str,
        operation_name: str,
        func: Callable[..., Any],
        *args: Any,
        cost: int = 1,
        **kwargs: Any,
    ) -> Any:
        if self.ctx.mode in {"dry-run", "cache-only"}:
            self.ctx.add_provider_event(
                provider=provider_name,
                event_type="skipped_by_mode",
                message=f"Skipped operation={operation_name} due to mode={self.ctx.mode}",
                metadata={"operation_name": operation_name, "mode": self.ctx.mode},
            )
            raise ProviderExecutionBlockedError(
                f"Provider execution skipped for provider={provider_name} due to mode={self.ctx.mode}"
            )

        if not self.provider_control_service.can_execute(provider_name):
            self.ctx.add_provider_event(
                provider=provider_name,
                event_type="blocked",
                message=f"Execution blocked for operation={operation_name}",
                metadata={"operation_name": operation_name},
            )
            raise ProviderExecutionBlockedError(
                f"Provider execution blocked for provider={provider_name} operation={operation_name}"
            )

        try:
            self.provider_control_service.consume_budget(provider_name, amount=cost)
        except BudgetExceededError as exc:
            self.ctx.add_provider_event(
                provider=provider_name,
                event_type="budget_exceeded",
                message=str(exc),
                metadata={"operation_name": operation_name, "cost": cost},
            )
            self.provider_control_service.register_provider_failure(provider_name, "budget_exceeded")
            raise

        retry_policy = self.provider_control_service.get_retry_policy(provider_name)
        last_exception: Exception | None = None

        for attempt in range(1, retry_policy.max_attempts + 1):
            if attempt > 1:
                delay = retry_policy.get_delay(attempt)
                self.ctx.add_provider_event(
                    provider=provider_name,
                    event_type="retry_scheduled",
                    message=f"Retry scheduled for operation={operation_name}",
                    metadata={
                        "operation_name": operation_name,
                        "attempt": attempt,
                        "delay_seconds": delay,
                    },
                )
                self.ctx.metrics[f"{provider_name}_retry_count"] = (
                    int(self.ctx.metrics.get(f"{provider_name}_retry_count", 0)) + 1
                )
                time.sleep(delay)

            self.ctx.add_provider_event(
                provider=provider_name,
                event_type="request_started",
                message=f"Starting operation={operation_name}",
                metadata={"operation_name": operation_name, "cost": cost, "attempt": attempt},
            )

            try:
                result = func(*args, **kwargs)
                self.provider_control_service.register_provider_success(provider_name)
                self.ctx.add_provider_event(
                    provider=provider_name,
                    event_type="request_succeeded",
                    message=f"Completed operation={operation_name}",
                    metadata={"operation_name": operation_name, "attempt": attempt},
                )
                return result
            except TimeoutError as exc:
                last_exception = exc
                self.provider_control_service.register_provider_failure(provider_name, "timeout")
                self.ctx.add_provider_event(
                    provider=provider_name,
                    event_type="timeout",
                    message=str(exc),
                    metadata={"operation_name": operation_name, "attempt": attempt},
                )
            except Exception as exc:
                last_exception = exc
                self.provider_control_service.register_provider_failure(provider_name, "execution_error")
                self.ctx.add_provider_event(
                    provider=provider_name,
                    event_type="execution_error",
                    message=str(exc),
                    metadata={"operation_name": operation_name, "attempt": attempt},
                )

        raise ProviderExecutionError(
            f"Provider execution failed after retries for provider={provider_name} operation={operation_name}"
        ) from last_exception
