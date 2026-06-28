from __future__ import annotations

from typing import Any

from oie.orchestration.lead_ranking_stage import LeadRankingStage
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem
from oie.services.master_dedup_service import MasterDedupService


class LeadDedupStage(Stage):
    name = "lead_dedup"
    order = 14

    def load_input(self) -> list[StageItem]:
        return StageCheckpointManager(LeadRankingStage(self.ctx)).read_output()

    def process_item(self, item: StageItem) -> StageItem:
        payload = self._payload_from_item(item)
        company = self._company_from_payload(payload)

        if payload.get("lead_generation_skipped") is True:
            return {
                "id": str(item.get("id") or company.get("company") or "lead_dedup_company"),
                "value": {
                    **payload,
                    "deduped_leads": [],
                    "duplicate_leads": [],
                    "lead_dedup_skipped": True,
                },
                "metadata": dict(item.get("metadata") or {}),
            }

        ranked_leads = self._list_from_payload(payload, "ranked_leads")
        selected_leads = self._list_from_payload(payload, "selected_leads")

        leads_to_dedupe = selected_leads or ranked_leads
        deduped_leads, duplicate_leads = MasterDedupService(
            self.ctx
        ).dedupe_leads_against_master(leads_to_dedupe)

        return {
            "id": str(item.get("id") or company.get("company") or "lead_dedup_company"),
            "value": {
                **payload,
                "deduped_leads": deduped_leads,
                "duplicate_leads": duplicate_leads,
                "lead_dedup_skipped": False,
            },
            "metadata": dict(item.get("metadata") or {}),
        }

    def _payload_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("LeadDedupStage item value must be a payload object.")
        return dict(value)

    def _company_from_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        company = payload.get("company") or {}
        if not isinstance(company, dict):
            raise TypeError("LeadDedupStage payload company must be a company object.")
        return dict(company)

    def _list_from_payload(self, payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
        value = payload.get(key) or []
        if not isinstance(value, list):
            raise TypeError(f"LeadDedupStage payload {key} must be a list.")
        return [dict(item) for item in value if isinstance(item, dict)]
