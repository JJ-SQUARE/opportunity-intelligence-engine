from __future__ import annotations

from typing import Any

from oie.orchestration.lead_dedup_stage import LeadDedupStage
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem
from oie.services.persistence_service import PersistenceService


class SnapshotPersistenceStage(Stage):
    name = "snapshot_persistence"
    order = 15

    def load_input(self) -> list[StageItem]:
        return StageCheckpointManager(LeadDedupStage(self.ctx)).read_output()

    def process_item(self, item: StageItem) -> StageItem:
        payload = self._payload_from_item(item)
        company = self._company_from_payload(payload)
        deduped_leads = self._list_from_payload(payload, "deduped_leads")
        duplicate_leads = self._list_from_payload(payload, "duplicate_leads")

        PersistenceService(self.ctx).persist_run_snapshot(
            status="company_pipeline_completed",
            companies=[company],
            leads=deduped_leads,
        )

        return {
            "id": str(item.get("id") or company.get("company") or "snapshot_persistence_company"),
            "value": {
                **payload,
                "snapshot_persisted": True,
                "snapshot_status": "company_pipeline_completed",
                "snapshot_companies_count": 1,
                "snapshot_leads_count": len(deduped_leads),
                "snapshot_duplicate_leads_count": len(duplicate_leads),
            },
            "metadata": dict(item.get("metadata") or {}),
        }

    def _payload_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("SnapshotPersistenceStage item value must be a payload object.")
        return dict(value)

    def _company_from_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        company = payload.get("company") or {}
        if not isinstance(company, dict):
            raise TypeError("SnapshotPersistenceStage payload company must be a company object.")
        return dict(company)

    def _list_from_payload(self, payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
        value = payload.get(key) or []
        if not isinstance(value, list):
            raise TypeError(f"SnapshotPersistenceStage payload {key} must be a list.")
        return [dict(item) for item in value if isinstance(item, dict)]
