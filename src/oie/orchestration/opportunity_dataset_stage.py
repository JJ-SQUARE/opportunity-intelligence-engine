from __future__ import annotations

from typing import Any

from oie.orchestration.snapshot_persistence_stage import SnapshotPersistenceStage
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem
from oie.services.opportunity_dataset_export_service import OpportunityDatasetExportService
from oie.services.opportunity_dataset_service import OpportunityDatasetService


class OpportunityDatasetStage(Stage):
    name = "opportunity_dataset"
    order = 16

    def load_input(self) -> list[StageItem]:
        return StageCheckpointManager(SnapshotPersistenceStage(self.ctx)).read_output()

    def process_item(self, item: StageItem) -> StageItem:
        payload = self._payload_from_item(item)

        dataset_service = OpportunityDatasetService(self.ctx)
        export_service = OpportunityDatasetExportService(self.ctx)

        dataset = dataset_service.build_dataset()
        top_dataset = dataset_service.build_top_opportunities(limit=25)

        dataset_path = export_service.export_dataset(dataset)
        top_dataset_path = export_service.export_top_dataset(top_dataset)

        return {
            "id": str(item.get("id") or "opportunity_dataset"),
            "value": {
                **payload,
                "opportunity_dataset_exported": True,
                "opportunity_dataset_rows": len(dataset),
                "top_opportunity_dataset_rows": len(top_dataset),
                "opportunity_dataset_path": dataset_path,
                "top_opportunity_dataset_path": top_dataset_path,
            },
            "metadata": dict(item.get("metadata") or {}),
        }

    def _payload_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("OpportunityDatasetStage item value must be a payload object.")
        return dict(value)
