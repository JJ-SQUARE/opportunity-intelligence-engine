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


def _operation_metric_key(provider_name: str, operation_name: str, suffix: str) -> str:
    safe_provider = str(provider_name or "unknown").strip().lower().replace("-", "_").replace(" ", "_")
    safe_operation = str(operation_name or "unknown").strip().lower().replace("-", "_").replace(" ", "_")
    return f"{safe_provider}_{safe_operation}_{suffix}"


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
                retry_metric_key = _operation_metric_key(provider_name, operation_name, "retry_count")
                self.ctx.metrics[retry_metric_key] = (
                    int(self.ctx.metrics.get(retry_metric_key, 0)) + 1
                )
                time.sleep(delay)

            self.ctx.add_provider_event(
                provider=provider_name,
                event_type="request_started",
                message=f"Starting operation={operation_name}",
                metadata={"operation_name": operation_name, "cost": cost, "attempt": attempt},
            )
            started_metric_key = _operation_metric_key(provider_name, operation_name, "started")
            self.ctx.metrics[started_metric_key] = (
                int(self.ctx.metrics.get(started_metric_key, 0)) + 1
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
                success_metric_key = _operation_metric_key(provider_name, operation_name, "success")
                self.ctx.metrics[success_metric_key] = (
                    int(self.ctx.metrics.get(success_metric_key, 0)) + 1
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
                timeout_metric_key = _operation_metric_key(provider_name, operation_name, "errors_timeout")
                self.ctx.metrics[timeout_metric_key] = (
                    int(self.ctx.metrics.get(timeout_metric_key, 0)) + 1
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
                execution_error_metric_key = _operation_metric_key(provider_name, operation_name, "errors_execution_error")
                self.ctx.metrics[execution_error_metric_key] = (
                    int(self.ctx.metrics.get(execution_error_metric_key, 0)) + 1
                )

        raise ProviderExecutionError(
            f"Provider execution failed after retries for provider={provider_name} operation={operation_name}"
        ) from last_exception
