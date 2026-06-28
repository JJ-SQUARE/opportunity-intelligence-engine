from __future__ import annotations

from typing import Any

from oie.orchestration.opportunity_dataset_stage import OpportunityDatasetStage
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem
from oie.services.opportunity_dataset_export_service import OpportunityDatasetExportService


class OpportunityDatasetExportStage(Stage):
    name = "opportunity_dataset_export"
    order = 17

    def load_input(self) -> list[StageItem]:
        return StageCheckpointManager(OpportunityDatasetStage(self.ctx)).read_output()

    def process_item(self, item: StageItem) -> StageItem:
        payload = self._payload_from_item(item)
        dataset = self._list_from_payload(payload, "dataset")
        top_dataset = self._list_from_payload(payload, "top_dataset")

        export_service = OpportunityDatasetExportService(self.ctx)
        dataset_path = export_service.export_dataset(dataset)
        top_dataset_path = export_service.export_top_dataset(top_dataset)

        return {
            "id": str(item.get("id") or "opportunity_dataset_export"),
            "value": {
                **payload,
                "dataset_exported": True,
                "dataset_path": dataset_path,
                "top_dataset_path": top_dataset_path,
                "dataset_rows": len(dataset),
                "top_dataset_rows": len(top_dataset),
            },
            "metadata": dict(item.get("metadata") or {}),
        }

    def _payload_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("OpportunityDatasetExportStage item value must be a payload object.")
        return dict(value)

    def _list_from_payload(self, payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
        value = payload.get(key) or []
        if not isinstance(value, list):
            raise TypeError(f"OpportunityDatasetExportStage payload {key} must be a list.")
        return [dict(item) for item in value if isinstance(item, dict)]
