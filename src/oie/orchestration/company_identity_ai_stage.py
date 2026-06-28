from __future__ import annotations

from typing import Any

from oie.orchestration.ai_company_gate_stage import AICompanyGateStage
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem
from oie.services.company_identity_ai_service import CompanyIdentityAIService
from oie.services.provider_control_service import ProviderControlService


class CompanyIdentityAIStage(Stage):
    name = "icp_match"
    order = 6

    def load_input(self) -> list[StageItem]:
        return StageCheckpointManager(AICompanyGateStage(self.ctx)).read_output()

    def process_item(self, item: StageItem) -> StageItem:
        company = self._company_from_item(item)

        if company.get("ai_company_gate_status") == "rejected":
            return {
                "id": str(item.get("id") or company.get("company") or "company_identity_ai_company"),
                "value": company,
                "metadata": dict(item.get("metadata") or {}),
            }

        provider_control_service = ProviderControlService(self.ctx)
        provider_control_service.initialize()
        provider_control_service.sync_budget_metrics()

        enriched_companies = CompanyIdentityAIService(
            self.ctx,
            provider_control_service,
        ).enrich_companies([company])
        enriched_company = enriched_companies[0] if enriched_companies else {
            **company,
            "company_identity_ai_discarded": True,
        }

        return {
            "id": str(item.get("id") or enriched_company.get("company") or "company_identity_ai_company"),
            "value": enriched_company,
            "metadata": dict(item.get("metadata") or {}),
        }

    def _company_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("CompanyIdentityAIStage item value must be a company object.")
        return dict(value)
