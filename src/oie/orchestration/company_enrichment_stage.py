from __future__ import annotations

from typing import Any

from oie.orchestration.domain_resolution_stage import DomainResolutionStage
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem
from oie.services.company_enrichment_service import CompanyEnrichmentService
from oie.services.provider_control_service import ProviderControlService


class CompanyEnrichmentStage(Stage):
    name = "delivery"
    order = 8

    def load_input(self) -> list[StageItem]:
        return StageCheckpointManager(DomainResolutionStage(self.ctx)).read_output()

    def process_item(self, item: StageItem) -> StageItem:
        company = self._company_from_item(item)

        if company.get("company_identity_ai_discarded") is True:
            return {
                "id": str(item.get("id") or company.get("company") or "company_enrichment_company"),
                "value": company,
                "metadata": dict(item.get("metadata") or {}),
            }

        provider_control_service = ProviderControlService(self.ctx)
        provider_control_service.initialize()
        provider_control_service.sync_budget_metrics()

        enriched_companies = CompanyEnrichmentService(
            self.ctx,
            provider_control_service,
        ).enrich_companies([company])
        enriched_company = enriched_companies[0] if enriched_companies else company

        return {
            "id": str(item.get("id") or enriched_company.get("company") or "company_enrichment_company"),
            "value": enriched_company,
            "metadata": dict(item.get("metadata") or {}),
        }

    def _company_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("CompanyEnrichmentStage item value must be a company object.")
        return dict(value)
