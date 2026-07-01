from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import ProviderExecutionService


class UrgencyService:
    def __init__(
        self,
        ctx: RunContext,
        provider_control_service: ProviderControlService,
    ) -> None:
        self.ctx = ctx
        self.provider_control_service = provider_control_service
        self.provider_execution_service = ProviderExecutionService(ctx, provider_control_service)

    def _is_ai_enabled(self) -> bool:
        config = self.ctx.config.get("urgency_gate", {}) or {}
        return bool(config.get("enabled", True)) and not bool(self.ctx.flags.get("no_llm"))

    def _fallback_urgency(self, reason: str) -> Dict[str, Any]:
        return {
            "days_old_estimate": -1,
            "freshness_score": 5.0,
            "freshness_bucket": "unknown",
            "urgency_score": 0.0,
            "should_advance": True,
            "reason": reason,
            "urgency_provider": "fallback",
            "urgency_model": "",
        }

    def analyze_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self._is_ai_enabled():
            self.ctx.metrics["urgency_gate_skipped_disabled"] = True
            return [{**job, "urgency": self._fallback_urgency("disabled")} for job in jobs]

        client = self.provider_control_service.registry.get_client("openai")
        if client is None:
            self.ctx.metrics["urgency_gate_skipped_no_client"] = True
            return [{**job, "urgency": self._fallback_urgency("no_client")} for job in jobs]

        results = []
        advanced = 0
        blocked = 0

        for job in jobs:
            record = dict(job)
            try:
                urgency = self.provider_execution_service.execute(
                    "openai",
                    "analyze_urgency",
                    client.analyze_urgency,
                    record,
                    cost=1,
                )
                record["urgency"] = urgency
                if urgency.get("should_advance", True):
                    advanced += 1
                else:
                    blocked += 1
            except Exception:
                record["urgency"] = self._fallback_urgency("ai_failed")
                advanced += 1

            results.append(record)

        self.ctx.metrics["urgency_gate_advanced"] = advanced
        self.ctx.metrics["urgency_gate_blocked"] = blocked
        self.ctx.metrics["urgency_gate_completed"] = True
        return results
