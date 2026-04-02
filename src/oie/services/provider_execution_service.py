from __future__ import annotations

import time

import requests
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

    def _get_operation_limit(self, provider_name: str, operation_name: str) -> int | None:
        providers_cfg = (self.ctx.config or {}).get("providers", {})
        operation_limits = providers_cfg.get("operation_limits", {}) or {}
        provider_limits = operation_limits.get(provider_name, {}) or {}
        raw_limit = provider_limits.get(operation_name)
        if raw_limit is None:
            return None
        return int(raw_limit)

    def _get_operation_used_metric_key(self, provider_name: str, operation_name: str) -> str:
        return _operation_metric_key(provider_name, operation_name, "used_calls")

    def _get_operation_blocked_metric_key(self, provider_name: str, operation_name: str) -> str:
        return _operation_metric_key(provider_name, operation_name, "blocked_budget")

    def _can_execute_operation(self, provider_name: str, operation_name: str, cost: int) -> bool:
        limit = self._get_operation_limit(provider_name, operation_name)
        if limit is None:
            return True

        used_key = self._get_operation_used_metric_key(provider_name, operation_name)
        used = int(self.ctx.metrics.get(used_key, 0))
        return used + cost <= limit

    def _consume_operation_budget(self, provider_name: str, operation_name: str, cost: int) -> None:
        limit = self._get_operation_limit(provider_name, operation_name)
        used_key = self._get_operation_used_metric_key(provider_name, operation_name)

        self.ctx.metrics[used_key] = int(self.ctx.metrics.get(used_key, 0)) + cost

        if limit is not None:
            max_key = _operation_metric_key(provider_name, operation_name, "max_calls")
            remaining_key = _operation_metric_key(provider_name, operation_name, "remaining_calls")
            used = int(self.ctx.metrics.get(used_key, 0))
            self.ctx.metrics[max_key] = limit
            self.ctx.metrics[remaining_key] = max(limit - used, 0)

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
            blocked_provider_key = _operation_metric_key(provider_name, operation_name, "blocked_provider")
            self.ctx.metrics[blocked_provider_key] = (
                int(self.ctx.metrics.get(blocked_provider_key, 0)) + 1
            )
            self.ctx.add_provider_event(
                provider=provider_name,
                event_type="blocked",
                message=f"Execution blocked for operation={operation_name}",
                metadata={"operation_name": operation_name},
            )
            raise ProviderExecutionBlockedError(
                f"Provider execution blocked for provider={provider_name} operation={operation_name}"
            )

        if not self._can_execute_operation(provider_name, operation_name, cost):
            blocked_metric_key = self._get_operation_blocked_metric_key(provider_name, operation_name)
            self.ctx.metrics[blocked_metric_key] = int(self.ctx.metrics.get(blocked_metric_key, 0)) + 1
            self.ctx.add_provider_event(
                provider=provider_name,
                event_type="operation_budget_blocked",
                message=f"Operation budget blocked for operation={operation_name}",
                metadata={"operation_name": operation_name, "cost": cost},
            )
            raise ProviderExecutionBlockedError(
                f"Operation budget blocked for provider={provider_name} operation={operation_name}"
            )

        try:
            self.provider_control_service.consume_budget(provider_name, amount=cost)
            self._consume_operation_budget(provider_name, operation_name, cost)
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
            except requests.exceptions.HTTPError as exc:
                last_exception = exc
                response = getattr(exc, "response", None)
                status_code = getattr(response, "status_code", None)

                if status_code == 429:
                    self.provider_control_service.register_provider_failure(provider_name, "rate_limit")
                    self.ctx.add_provider_event(
                        provider=provider_name,
                        event_type="rate_limit",
                        message=str(exc),
                        metadata={
                            "operation_name": operation_name,
                            "attempt": attempt,
                            "status_code": status_code,
                        },
                    )
                    metric_key = _operation_metric_key(provider_name, operation_name, "errors_rate_limit")
                    self.ctx.metrics[metric_key] = (
                        int(self.ctx.metrics.get(metric_key, 0)) + 1
                    )
                elif status_code is not None and 500 <= int(status_code) < 600:
                    self.provider_control_service.register_provider_failure(provider_name, "http_5xx")
                    self.ctx.add_provider_event(
                        provider=provider_name,
                        event_type="http_5xx",
                        message=str(exc),
                        metadata={
                            "operation_name": operation_name,
                            "attempt": attempt,
                            "status_code": status_code,
                        },
                    )
                    metric_key = _operation_metric_key(provider_name, operation_name, "errors_http_5xx")
                    self.ctx.metrics[metric_key] = (
                        int(self.ctx.metrics.get(metric_key, 0)) + 1
                    )
                else:
                    self.provider_control_service.register_provider_failure(provider_name, "execution_error")
                    self.ctx.add_provider_event(
                        provider=provider_name,
                        event_type="execution_error",
                        message=str(exc),
                        metadata={
                            "operation_name": operation_name,
                            "attempt": attempt,
                            "status_code": status_code,
                        },
                    )
                    metric_key = _operation_metric_key(provider_name, operation_name, "errors_execution_error")
                    self.ctx.metrics[metric_key] = (
                        int(self.ctx.metrics.get(metric_key, 0)) + 1
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
