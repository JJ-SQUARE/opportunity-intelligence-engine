from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import ProviderExecutionService


class CompanyClassificationService:
    def __init__(
        self,
        ctx: RunContext,
        provider_control_service: ProviderControlService,
    ) -> None:
        self.ctx = ctx
        self.provider_control_service = provider_control_service
        self.provider_execution_service = ProviderExecutionService(ctx, provider_control_service)

    def classify_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self.ctx.flags.get("no_llm"):
            self.ctx.metrics["company_classification_skipped_no_llm"] = True
            return companies

        client = self.provider_control_service.registry.get_client("openai")
        if client is None:
            self.ctx.metrics["company_classification_skipped_no_client"] = True
            return companies

        classified: List[Dict[str, Any]] = []

        for company in companies:
            result = self.provider_execution_service.execute(
                "openai",
                "classify_company",
                client.classify_company,
                company,
                cost=1,
            )

            enriched = dict(company)
            enriched["company_type_ai"] = result.get("classification")
            enriched["classification_confidence_ai"] = result.get("confidence")
            enriched["classification_provider"] = result.get("provider")
            classified.append(enriched)

        self.ctx.metrics["companies_classified"] = len(classified)
        return classified
