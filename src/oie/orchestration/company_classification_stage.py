from __future__ import annotations

from typing import Any

from oie.orchestration.company_enrichment_stage import CompanyEnrichmentStage
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem
from oie.services.company_classification_service import CompanyClassificationService
from oie.services.provider_control_service import ProviderControlService


class CompanyClassificationStage(Stage):
    name = "company_classification"
    order = 9

    def load_input(self) -> list[StageItem]:
        return StageCheckpointManager(CompanyEnrichmentStage(self.ctx)).read_output()

    def process_item(self, item: StageItem) -> StageItem:
        company = self._company_from_item(item)

        if company.get("company_identity_ai_discarded") is True:
            return {
                "id": str(item.get("id") or company.get("company") or "company_classification_company"),
                "value": company,
                "metadata": dict(item.get("metadata") or {}),
            }

        provider_control_service = ProviderControlService(self.ctx)
        provider_control_service.initialize()
        provider_control_service.sync_budget_metrics()

        classified = CompanyClassificationService(
            self.ctx,
            provider_control_service,
        ).classify_companies([company])
        classified_company = classified[0] if classified else company

        return {
            "id": str(item.get("id") or classified_company.get("company") or "company_classification_company"),
            "value": classified_company,
            "metadata": dict(item.get("metadata") or {}),
        }

    def _company_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("CompanyClassificationStage item value must be a company object.")
        return dict(value)
