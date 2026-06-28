from __future__ import annotations

from typing import Any

from oie.orchestration.company_limit_stage import CompanyLimitStage
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem
from oie.services.lead_generation_service import LeadGenerationService
from oie.services.provider_control_service import ProviderControlService


class LeadGenerationStage(Stage):
    name = "lead_contact_generation"
    order = 12

    def load_input(self) -> list[StageItem]:
        return StageCheckpointManager(CompanyLimitStage(self.ctx)).read_output()

    def process_item(self, item: StageItem) -> StageItem:
        company = self._company_from_item(item)

        if (
            company.get("company_identity_ai_discarded") is True
            or company.get("company_limit_excluded") is True
        ):
            return {
                "id": str(item.get("id") or company.get("company") or "lead_generation_company"),
                "value": {
                    "company": company,
                    "leads": [],
                    "lead_generation_skipped": True,
                },
                "metadata": dict(item.get("metadata") or {}),
            }

        provider_control_service = ProviderControlService(self.ctx)
        provider_control_service.initialize()
        provider_control_service.sync_budget_metrics()

        leads = LeadGenerationService(
            self.ctx,
            provider_control_service,
        ).generate_leads([company])

        return {
            "id": str(item.get("id") or company.get("company") or "lead_generation_company"),
            "value": {
                "company": company,
                "leads": leads,
                "lead_generation_skipped": False,
            },
            "metadata": dict(item.get("metadata") or {}),
        }

    def _company_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("LeadGenerationStage item value must be a company object.")
        return dict(value)
