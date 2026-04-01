from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from oie.orchestration.run_context import RunContext


KNOWN_SUFFIXES = [
    "max_calls",
    "used_calls",
    "remaining_calls",
    "started",
    "success",
    "retry_count",
    "blocked_budget",
    "errors_timeout",
    "errors_execution_error",
]


class ProviderOperationMetricsService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def _parse_metric_key(self, metric_key: str) -> Tuple[str, str, str] | None:
        for suffix in KNOWN_SUFFIXES:
            ending = f"_{suffix}"
            if not metric_key.endswith(ending):
                continue

            base = metric_key[: -len(ending)]
            if "_" not in base:
                return None

            provider, operation = base.split("_", 1)
            if not provider or not operation:
                return None

            return provider, operation, suffix

        return None

    def build_rows(self) -> List[Dict[str, Any]]:
        grouped: Dict[Tuple[str, str], Dict[str, Any]] = {}

        for metric_key, metric_value in self.ctx.metrics.items():
            parsed = self._parse_metric_key(metric_key)
            if not parsed:
                continue

            provider, operation, suffix = parsed
            row_key = (provider, operation)

            if row_key not in grouped:
                grouped[row_key] = {
                    "provider": provider,
                    "operation": operation,
                    "max_calls": None,
                    "used_calls": 0,
                    "remaining_calls": None,
                    "started": 0,
                    "success": 0,
                    "retry_count": 0,
                    "blocked_budget": 0,
                    "errors_timeout": 0,
                    "errors_execution_error": 0,
                }

            grouped[row_key][suffix] = metric_value

        rows = list(grouped.values())
        rows.sort(key=lambda r: (r["provider"], r["operation"]))
        self.ctx.metrics["provider_operation_metrics_rows"] = len(rows)
        return rows
