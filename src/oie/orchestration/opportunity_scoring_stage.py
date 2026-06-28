from __future__ import annotations

from typing import Any

from oie.orchestration.company_classification_stage import CompanyClassificationStage
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem
from oie.services.opportunity_scoring_service import OpportunityScoringService
from oie.services.provider_control_service import ProviderControlService


class OpportunityScoringStage(Stage):
    name = "opportunity_scoring"
    order = 10

    def load_input(self) -> list[StageItem]:
        return StageCheckpointManager(CompanyClassificationStage(self.ctx)).read_output()

    def process_item(self, item: StageItem) -> StageItem:
        company = self._company_from_item(item)

        if company.get("company_identity_ai_discarded") is True:
            return {
                "id": str(item.get("id") or company.get("company") or "opportunity_scoring_company"),
                "value": company,
                "metadata": dict(item.get("metadata") or {}),
            }

        provider_control_service = ProviderControlService(self.ctx)
        provider_control_service.initialize()
        provider_control_service.sync_budget_metrics()

        scored = OpportunityScoringService(
            self.ctx,
            provider_control_service,
        ).score_companies([company])
        scored_company = scored[0] if scored else company

        return {
            "id": str(item.get("id") or scored_company.get("company") or "opportunity_scoring_company"),
            "value": scored_company,
            "metadata": dict(item.get("metadata") or {}),
        }

    def _company_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("OpportunityScoringStage item value must be a company object.")
        return dict(value)
