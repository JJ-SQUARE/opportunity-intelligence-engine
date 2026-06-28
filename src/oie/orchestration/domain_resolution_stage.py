from __future__ import annotations

from typing import Any

from oie.orchestration.company_identity_ai_stage import CompanyIdentityAIStage
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem
from oie.services.domain_resolution_service import DomainResolutionService
from oie.services.provider_control_service import ProviderControlService


class DomainResolutionStage(Stage):
    name = "lead_generation"
    order = 7

    def load_input(self) -> list[StageItem]:
        return StageCheckpointManager(CompanyIdentityAIStage(self.ctx)).read_output()

    def process_item(self, item: StageItem) -> StageItem:
        company = self._company_from_item(item)

        if company.get("company_identity_ai_discarded") is True:
            return {
                "id": str(item.get("id") or company.get("company") or "domain_resolution_company"),
                "value": company,
                "metadata": dict(item.get("metadata") or {}),
            }

        provider_control_service = ProviderControlService(self.ctx)
        provider_control_service.initialize()
        provider_control_service.sync_budget_metrics()

        resolved_companies = DomainResolutionService(
            self.ctx,
            provider_control_service,
        ).resolve_domains([company])
        resolved_company = resolved_companies[0] if resolved_companies else company

        return {
            "id": str(item.get("id") or resolved_company.get("company") or "domain_resolution_company"),
            "value": resolved_company,
            "metadata": dict(item.get("metadata") or {}),
        }

    def _company_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("DomainResolutionStage item value must be a company object.")
        return dict(value)
