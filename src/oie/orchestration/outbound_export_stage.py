from __future__ import annotations

from typing import Any

from oie.orchestration.opportunity_dataset_export_stage import OpportunityDatasetExportStage
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem
from oie.services.outbound_export_service import OutboundExportService
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import ProviderExecutionService


class OutboundExportStage(Stage):
    name = "outbound_export"
    order = 18

    def load_input(self) -> list[StageItem]:
        return StageCheckpointManager(OpportunityDatasetExportStage(self.ctx)).read_output()

    def process_item(self, item: StageItem) -> StageItem:
        payload = self._payload_from_item(item)

        provider_control_service = ProviderControlService(self.ctx)
        provider_control_service.initialize()
        provider_control_service.sync_budget_metrics()
        provider_execution_service = ProviderExecutionService(self.ctx, provider_control_service)

        service = OutboundExportService(self.ctx)
        export_result = service.export_all()
        hubspot_push_result = service.push_hubspot_payloads(provider_execution_service)

        self.ctx.provider_state["hubspot_push_result"] = hubspot_push_result

        return {
            "id": str(item.get("id") or "outbound_export"),
            "value": {
                **payload,
                "outbound_exported": True,
                "outbound_export_result": export_result,
                "hubspot_push_result": hubspot_push_result,
            },
            "metadata": dict(item.get("metadata") or {}),
        }

    def _payload_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("OutboundExportStage item value must be a payload object.")
        return dict(value)
