from __future__ import annotations

from typing import Any

from oie.orchestration.lead_generation_stage import LeadGenerationStage
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem
from oie.services.lead_ranking_service import LeadRankingService
from oie.services.provider_control_service import ProviderControlService


class LeadRankingStage(Stage):
    name = "lead_ranking"
    order = 13

    def load_input(self) -> list[StageItem]:
        return StageCheckpointManager(LeadGenerationStage(self.ctx)).read_output()

    def process_item(self, item: StageItem) -> StageItem:
        payload = self._payload_from_item(item)
        company = dict(payload.get("company") or {})
        leads = payload.get("leads") or []

        if payload.get("lead_generation_skipped") is True:
            return {
                "id": str(item.get("id") or company.get("company") or "lead_ranking_company"),
                "value": {
                    **payload,
                    "ranked_leads": [],
                    "selected_leads": [],
                    "lead_ranking_skipped": True,
                },
                "metadata": dict(item.get("metadata") or {}),
            }

        if not isinstance(leads, list):
            raise TypeError("LeadRankingStage payload leads must be a list.")

        provider_control_service = ProviderControlService(self.ctx)
        provider_control_service.initialize()
        provider_control_service.sync_budget_metrics()

        service = LeadRankingService(self.ctx, provider_control_service)
        ranked_leads = service.rank_leads([dict(lead) for lead in leads if isinstance(lead, dict)])

        lead_cfg = self.ctx.config.get("lead_generation", {}) or {}
        max_selected = int(lead_cfg.get("max_selected_leads_per_company", 3) or 3)
        max_selected = max(1, max_selected)

        selected_leads = service.select_top_leads_per_company(
            ranked_leads,
            max_leads_per_company=max_selected,
        )
        self.ctx.metrics["pipeline_selected_leads_per_company"] = max_selected

        return {
            "id": str(item.get("id") or company.get("company") or "lead_ranking_company"),
            "value": {
                **payload,
                "ranked_leads": ranked_leads,
                "selected_leads": selected_leads,
                "lead_ranking_skipped": False,
            },
            "metadata": dict(item.get("metadata") or {}),
        }

    def _payload_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("LeadRankingStage item value must be a lead generation payload object.")
        return dict(value)
