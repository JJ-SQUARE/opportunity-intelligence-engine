from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import ProviderExecutionService


DEFAULT_JOB_INTELLIGENCE = {
    "is_real_job": True,
    "is_contaminated": False,
    "real_company_name": "",
    "confidence": 0.0,
    "usable_for_scoring": True,
    "role": "",
    "seniority": "",
    "tech_stack": [],
    "budget": "",
    "workplace_type": "",
    "commercial_signals": [],
}


class JobIntelligenceService:
    SERP_SOURCES = {
        "linkedin_serpapi",
        "indeed_serpapi",
        "career_pages_serpapi",
        "google_jobs",
    }

    def __init__(
        self,
        ctx: RunContext,
        provider_control_service: ProviderControlService,
    ) -> None:
        self.ctx = ctx
        self.provider_control_service = provider_control_service
        self.provider_execution_service = ProviderExecutionService(ctx, provider_control_service)

    def _is_ai_enabled(self) -> bool:
        config = (self.ctx.config.get("job_intelligence", {}) or {})
        return bool(config.get("enabled", True)) and not bool(self.ctx.flags.get("no_llm"))

    def _should_analyze_job(self, job: Dict[str, Any]) -> bool:
        source = str(job.get("source") or "").strip().lower()
        return source in self.SERP_SOURCES

    def _max_jobs_to_analyze(self) -> int | None:
        config = (self.ctx.config.get("job_intelligence", {}) or {})
        raw_limit = config.get("max_jobs_to_analyze")
        if raw_limit in (None, "", 0, "0", False):
            return None
        return max(0, int(raw_limit))

    def _fallback_intelligence(self, job: Dict[str, Any], reason: str) -> Dict[str, Any]:
        company = str(job.get("company") or "").strip()
        return {
            **DEFAULT_JOB_INTELLIGENCE,
            "real_company_name": company,
            "confidence": 0.0,
            "job_intelligence_provider": "fallback",
            "job_intelligence_mode": reason,
        }

    def _normalize_ai_result(self, job: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(DEFAULT_JOB_INTELLIGENCE)
        normalized.update(result or {})

        normalized["is_real_job"] = bool(normalized.get("is_real_job"))
        normalized["is_contaminated"] = bool(normalized.get("is_contaminated"))
        normalized["usable_for_scoring"] = bool(normalized.get("usable_for_scoring"))

        if not isinstance(normalized.get("tech_stack"), list):
            normalized["tech_stack"] = []
        if not isinstance(normalized.get("commercial_signals"), list):
            normalized["commercial_signals"] = []

        normalized["real_company_name"] = str(
            normalized.get("real_company_name") or job.get("company") or ""
        ).strip()
        normalized["role"] = str(normalized.get("role") or "").strip()
        normalized["seniority"] = str(normalized.get("seniority") or "").strip()
        normalized["budget"] = str(normalized.get("budget") or "").strip()
        normalized["workplace_type"] = str(normalized.get("workplace_type") or "").strip()

        try:
            normalized["confidence"] = float(normalized.get("confidence") or 0.0)
        except Exception:
            normalized["confidence"] = 0.0
        normalized["confidence"] = max(0.0, min(normalized["confidence"], 1.0))

        return normalized

    def _apply_intelligence_to_record(
        self,
        record: Dict[str, Any],
        intelligence: Dict[str, Any],
    ) -> Dict[str, Any]:
        updated = dict(record)
        updated["job_intelligence"] = intelligence
        updated["job_ai_usable_for_scoring"] = bool(intelligence.get("usable_for_scoring"))
        updated["job_ai_is_contaminated"] = bool(intelligence.get("is_contaminated"))
        updated["job_ai_confidence"] = float(intelligence.get("confidence") or 0.0)

        real_company_name = str(intelligence.get("real_company_name") or "").strip()
        if (
            real_company_name
            and bool(intelligence.get("is_real_job"))
            and not bool(intelligence.get("is_contaminated"))
            and bool(intelligence.get("usable_for_scoring"))
            and float(intelligence.get("confidence") or 0.0) >= 0.75
        ):
            updated["original_company"] = updated.get("company", "")
            updated["company"] = real_company_name
            updated["company_ai_overridden"] = True
            self.ctx.metrics["job_intelligence_company_overrides"] = (
                int(self.ctx.metrics.get("job_intelligence_company_overrides", 0) or 0) + 1
            )
        elif bool(intelligence.get("is_contaminated")) or not bool(intelligence.get("usable_for_scoring")):
            self.ctx.metrics["job_intelligence_not_usable_for_scoring"] = (
                int(self.ctx.metrics.get("job_intelligence_not_usable_for_scoring", 0) or 0) + 1
            )

        return updated

    def enrich_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self._is_ai_enabled():
            self.ctx.metrics["job_intelligence_skipped_disabled"] = True
            return jobs

        client = self.provider_control_service.registry.get_client("openai")
        if client is None:
            self.ctx.metrics["job_intelligence_skipped_no_client"] = True
            return jobs

        enriched_jobs: List[Dict[str, Any]] = []
        analyzed = 0
        fallback = 0

        for job in jobs:
            record = dict(job)

            if not self._should_analyze_job(record):
                intelligence = self._fallback_intelligence(record, "trusted_source_not_analyzed")
                enriched_jobs.append(self._apply_intelligence_to_record(record, intelligence))
                continue

            max_jobs_to_analyze = self._max_jobs_to_analyze()
            if max_jobs_to_analyze is not None and analyzed >= max_jobs_to_analyze:
                intelligence = self._fallback_intelligence(record, "job_intelligence_cap_reached")
                record = self._apply_intelligence_to_record(record, intelligence)
                fallback += 1
                enriched_jobs.append(record)
                continue

            try:
                result = self.provider_execution_service.execute(
                    "openai",
                    "analyze_job_intelligence",
                    client.analyze_job_intelligence,
                    record,
                    cost=1,
                )
                intelligence = self._normalize_ai_result(record, result)
                record = self._apply_intelligence_to_record(record, intelligence)
                analyzed += 1
            except Exception:
                intelligence = self._fallback_intelligence(record, "ai_failed")
                record = self._apply_intelligence_to_record(record, intelligence)
                fallback += 1

            enriched_jobs.append(record)

        self.ctx.metrics["job_intelligence_analyzed"] = analyzed
        self.ctx.metrics["job_intelligence_jobs_analyzed"] = analyzed
        self.ctx.metrics["jobs_analyzed_by_ai"] = analyzed
        self.ctx.metrics["job_intelligence_fallback"] = fallback
        max_jobs_to_analyze = self._max_jobs_to_analyze()
        if max_jobs_to_analyze is not None:
            self.ctx.metrics["job_intelligence_max_jobs_to_analyze"] = max_jobs_to_analyze
            self.ctx.metrics["job_intelligence_cap_reached"] = analyzed >= max_jobs_to_analyze
        self.ctx.metrics["job_intelligence_completed"] = True
        return enriched_jobs
