from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.orchestration.stage_errors import ProviderNotConfiguredError
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import ProviderExecutionBlockedError, ProviderExecutionService


PREFILTER_BLOCKED_NAMES = {
    "confidential", "confidentiel", "empresa confidencial",
    "empresa reservada", "undisclosed", "anonymous",
}

PREFILTER_JOB_BOARD_URL_HINTS = {
    "linkedin.com/jobs", "indeed.com", "glassdoor.com", "jobgether",
    "computrabajo", "bumeran", "jooble", "adzuna", "grabjobs",
}


class JobGateService:
    def __init__(
        self,
        ctx: RunContext,
        provider_control_service: ProviderControlService,
    ) -> None:
        self.ctx = ctx
        self.provider_control_service = provider_control_service
        self.provider_execution_service = ProviderExecutionService(ctx, provider_control_service)

    def _is_ai_enabled(self) -> bool:
        config = self.ctx.config.get("job_gate", {}) or {}
        return bool(config.get("enabled", True)) and not bool(self.ctx.flags.get("no_llm"))

    def _prefilter_blocked(self, job: Dict[str, Any]) -> str | None:
        company = str(job.get("company") or "").strip().lower()
        if company in PREFILTER_BLOCKED_NAMES:
            return f"confidential company name: {company}"

        job_url = str(job.get("job_url") or job.get("url") or "").strip().lower()
        for hint in PREFILTER_JOB_BOARD_URL_HINTS:
            if hint in job_url:
                return f"job board url: {hint}"

        return None

    def _fallback_gate(self, job: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return {
            "should_advance": True,
            "company_type": "unknown",
            "confidence": 0.0,
            "block_reason": "",
            "job_gate_provider": "fallback",
            "job_gate_mode": reason,
        }

    def _blocked_gate(self, job: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return {
            "should_advance": False,
            "company_type": "noise",
            "confidence": 1.0,
            "block_reason": reason,
            "job_gate_provider": "prefilter",
            "job_gate_mode": "prefilter",
        }

    def gate_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self._is_ai_enabled():
            self.ctx.metrics["job_gate_skipped_disabled"] = True
            return [
                {**job, "job_gate": self._fallback_gate(job, "disabled")}
                for job in jobs
            ]

        client = self.provider_control_service.registry.get_client("openai")
        if client is None or not client.is_configured():
            raise ProviderNotConfiguredError(
                "OpenAI client is not configured. "
                "Please set OPENAI_API_KEY and retry this stage."
            )

        results = []
        advanced = 0
        blocked = 0
        prefiltered = 0

        for job in jobs:
            record = dict(job)

            prefilter_reason = self._prefilter_blocked(record)
            if prefilter_reason:
                record["job_gate"] = self._blocked_gate(record, prefilter_reason)
                prefiltered += 1
                blocked += 1
                results.append(record)
                continue

            try:
                gate_result = self.provider_execution_service.execute(
                    "openai",
                    "gate_job",
                    client.gate_job,
                    record,
                    cost=1,
                )
                record["job_gate"] = gate_result
                if gate_result.get("should_advance", True):
                    advanced += 1
                else:
                    blocked += 1
            except (ProviderNotConfiguredError, ProviderExecutionBlockedError):
                raise
            except Exception:
                record["job_gate"] = self._fallback_gate(record, "ai_failed")
                self.ctx.metrics["job_gate_ai_failed"] = (
                    int(self.ctx.metrics.get("job_gate_ai_failed", 0)) + 1
                )

            results.append(record)

        self.ctx.metrics["job_gate_advanced"] = advanced
        self.ctx.metrics["job_gate_blocked"] = blocked
        self.ctx.metrics["job_gate_prefiltered"] = prefiltered
        self.ctx.metrics["job_gate_completed"] = True
        return results
