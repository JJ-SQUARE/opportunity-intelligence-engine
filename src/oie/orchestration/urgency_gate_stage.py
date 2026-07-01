from __future__ import annotations

from typing import Any

from oie.orchestration.job_gate_stage import JobGateStage
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem
from oie.services.provider_control_service import ProviderControlService
from oie.services.urgency_service import UrgencyService


class UrgencyGateStage(Stage):
    name = "urgency_gate"
    order = 4

    def load_input(self) -> list[StageItem]:
        return StageCheckpointManager(JobGateStage(self.ctx)).read_output()

    def process_item(self, item: StageItem) -> StageItem | None:
        job = self._job_from_item(item)

        provider_control_service = ProviderControlService(self.ctx)
        provider_control_service.initialize()
        provider_control_service.sync_budget_metrics()

        analyzed = UrgencyService(
            self.ctx,
            provider_control_service,
        ).analyze_jobs([job])

        result = analyzed[0] if analyzed else {}
        urgency = result.get("urgency", {})

        if not urgency.get("should_advance", True):
            self.ctx.metrics["urgency_gate_rejected"] = (
                int(self.ctx.metrics.get("urgency_gate_rejected", 0)) + 1
            )
            return None

        return {
            "id": str(item.get("id") or "unknown_job"),
            "value": {**dict(result), "urgency": urgency},
            "metadata": {
                **dict(item.get("metadata") or {}),
                "freshness_score": urgency.get("freshness_score"),
                "urgency_score": urgency.get("urgency_score"),
                "freshness_bucket": urgency.get("freshness_bucket"),
            },
        }

    def _job_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("UrgencyGateStage item value must be a job object.")
        return dict(value)
