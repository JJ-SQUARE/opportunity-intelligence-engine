from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import ProviderExecutionService


DEFAULT_COMPANY_IDENTITY_AI = {
    "is_valid_company": True,
    "is_contaminated": False,
    "is_ambiguous": False,
    "company_name": "",
    "identity_source": "unknown",
    "confidence": 0.0,
    "reason": "",
}


class CompanyIdentityAIService:
    def __init__(
        self,
        ctx: RunContext,
        provider_control_service: ProviderControlService,
    ) -> None:
        self.ctx = ctx
        self.provider_control_service = provider_control_service
        self.provider_execution_service = ProviderExecutionService(ctx, provider_control_service)

    def _is_ai_enabled(self) -> bool:
        config = (self.ctx.config.get("company_identity_ai", {}) or {})
        return bool(config.get("enabled", True)) and not bool(self.ctx.flags.get("no_llm"))

    def _normalize_ai_result(self, company: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(DEFAULT_COMPANY_IDENTITY_AI)
        normalized.update(result or {})

        normalized["is_valid_company"] = bool(normalized.get("is_valid_company"))
        normalized["is_contaminated"] = bool(normalized.get("is_contaminated"))
        normalized["is_ambiguous"] = bool(normalized.get("is_ambiguous"))
        normalized["company_name"] = str(
            normalized.get("company_name")
            or company.get("company_display")
            or company.get("company")
            or ""
        ).strip()
        normalized["identity_source"] = str(normalized.get("identity_source") or "unknown").strip().lower()
        normalized["reason"] = str(normalized.get("reason") or "").strip()

        try:
            normalized["confidence"] = float(normalized.get("confidence") or 0.0)
        except Exception:
            normalized["confidence"] = 0.0
        normalized["confidence"] = max(0.0, min(normalized["confidence"], 1.0))

        return normalized

    def _fallback_identity(self, company: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return {
            **DEFAULT_COMPANY_IDENTITY_AI,
            "company_name": str(company.get("company_display") or company.get("company") or "").strip(),
            "identity_source": "fallback",
            "reason": reason,
            "provider": "fallback",
        }

    def enrich_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self._is_ai_enabled():
            self.ctx.metrics["company_identity_ai_skipped_disabled"] = True
            return companies

        client = self.provider_control_service.registry.get_client("openai")
        if client is None:
            self.ctx.metrics["company_identity_ai_skipped_no_client"] = True
            return companies

        enriched_companies: List[Dict[str, Any]] = []
        analyzed = 0
        fallback = 0
        invalid = 0

        for company in companies:
            record = dict(company)

            try:
                result = self.provider_execution_service.execute(
                    "openai",
                    "resolve_company_identity",
                    client.resolve_company_identity,
                    record,
                    cost=1,
                )
                identity = self._normalize_ai_result(record, result)
                analyzed += 1
            except Exception:
                identity = self._fallback_identity(record, "ai_failed")
                fallback += 1

            record["ai_company_identity"] = identity
            record["ai_company_identity_confidence"] = identity.get("confidence")
            record["ai_company_identity_source"] = identity.get("identity_source")
            record["ai_company_identity_reason"] = identity.get("reason")
            record["company_identity_ai_valid"] = bool(identity.get("is_valid_company"))
            record["company_identity_ai_contaminated"] = bool(identity.get("is_contaminated"))
            record["company_identity_ai_ambiguous"] = bool(identity.get("is_ambiguous"))

            should_discard = (
                not bool(identity.get("is_valid_company"))
                or bool(identity.get("is_contaminated"))
                or bool(identity.get("is_ambiguous"))
            )
            record["company_identity_ai_discarded"] = should_discard

            if not bool(identity.get("is_valid_company")):
                invalid += 1
            if should_discard:
                self.ctx.metrics["company_identity_ai_discarded"] = (
                    int(self.ctx.metrics.get("company_identity_ai_discarded", 0) or 0) + 1
                )
                continue

            enriched_companies.append(record)

        self.ctx.metrics["company_identity_ai_analyzed"] = analyzed
        self.ctx.metrics["company_identity_ai_fallback"] = fallback
        self.ctx.metrics["company_identity_ai_invalid"] = invalid
        self.ctx.metrics["company_identity_ai_completed"] = True
        return enriched_companies
