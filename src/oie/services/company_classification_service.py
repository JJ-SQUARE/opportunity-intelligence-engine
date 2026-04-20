from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import ProviderExecutionService


RULE_KEYWORDS = {
    "staffing": ["staffing", "recruiting", "talent solutions", "headhunting"],
    "consulting": ["consulting", "consultancy", "professional services", "advisory"],
    "marketplace": ["marketplace", "platform", "two-sided marketplace"],
    "job_board": ["job board", "jobs board", "career portal", "job search"],
}


class CompanyClassificationService:
    def __init__(
        self,
        ctx: RunContext,
        provider_control_service: ProviderControlService,
    ) -> None:
        self.ctx = ctx
        self.provider_control_service = provider_control_service
        self.provider_execution_service = ProviderExecutionService(ctx, provider_control_service)

    def _rule_based_classification(self, company: Dict[str, Any]) -> Dict[str, Any] | None:
        text = " ".join(
            [
                str(company.get("company_display") or ""),
                str(company.get("company_description") or ""),
                str(company.get("industry") or ""),
            ]
        ).lower()

        for company_type, keywords in RULE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return {
                        "classification": company_type,
                        "confidence": 0.8,
                        "provider": "rules",
                    }

        if text.strip():
            return {
                "classification": "end_client",
                "confidence": 0.55,
                "provider": "rules",
            }

        return None

    def classify_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self.ctx.flags.get("no_llm"):
            classified = []
            for company in companies:
                enriched = dict(company)
                company_type = str(enriched.get("company_type_ai") or "").strip().lower()

                if enriched.get("benchmark_only") or company_type == "competitor":
                    enriched["company_type_ai"] = "competitor"
                    enriched["classification_confidence_ai"] = float(
                        enriched.get("classification_confidence_ai") or 1.0
                    )
                    enriched["classification_provider"] = (
                        enriched.get("classification_provider")
                        or enriched.get("classification_source")
                        or "benchmark_config"
                    )
                    classified.append(enriched)
                    continue

                rule_result = self._rule_based_classification(company)
                if rule_result:
                    enriched["company_type_ai"] = rule_result["classification"]
                    enriched["classification_confidence_ai"] = rule_result["confidence"]
                    enriched["classification_provider"] = rule_result["provider"]
                classified.append(enriched)

            self.ctx.metrics["company_classification_skipped_no_llm"] = True
            self.ctx.metrics["companies_classified"] = len(classified)
            return classified

        client = self.provider_control_service.registry.get_client("openai")
        if client is None:
            self.ctx.metrics["company_classification_skipped_no_client"] = True
            return companies

        classified: List[Dict[str, Any]] = []

        for company in companies:
            enriched = dict(company)
            company_type = str(enriched.get("company_type_ai") or "").strip().lower()

            if enriched.get("benchmark_only") or company_type == "competitor":
                enriched["company_type_ai"] = "competitor"
                enriched["classification_confidence_ai"] = float(
                    enriched.get("classification_confidence_ai") or 1.0
                )
                enriched["classification_provider"] = (
                    enriched.get("classification_provider")
                    or enriched.get("classification_source")
                    or "benchmark_config"
                )
                classified.append(enriched)
                continue

            try:
                result = self.provider_execution_service.execute(
                    "openai",
                    "classify_company",
                    client.classify_company,
                    company,
                    cost=1,
                )
            except Exception:
                result = self._rule_based_classification(company) or {
                    "classification": "unknown",
                    "confidence": 0.0,
                    "provider": "fallback_rules",
                }

            enriched["company_type_ai"] = result.get("classification")
            enriched["classification_confidence_ai"] = result.get("confidence")
            enriched["classification_provider"] = result.get("provider")
            classified.append(enriched)

        self.ctx.metrics["companies_classified"] = len(classified)
        return classified
