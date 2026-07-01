from __future__ import annotations

from typing import Any

from oie.orchestration.normalize_jobs_stage import NormalizeJobsStage
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem
from oie.services.job_gate_service import JobGateService
from oie.services.provider_control_service import ProviderControlService


class JobGateStage(Stage):
    name = "company_gate"
    order = 3

    def load_input(self) -> list[StageItem]:
        return StageCheckpointManager(NormalizeJobsStage(self.ctx)).read_output()

    def process_item(self, item: StageItem) -> StageItem | None:
        job = self._job_from_item(item)

        provider_control_service = ProviderControlService(self.ctx)
        provider_control_service.initialize()
        provider_control_service.sync_budget_metrics()

        gated = JobGateService(
            self.ctx,
            provider_control_service,
        ).gate_jobs([job])

        result = gated[0] if gated else {}
        gate = result.get("job_gate", {})

        if not gate.get("should_advance", True):
            self.ctx.metrics["company_gate_blocked"] = (
                int(self.ctx.metrics.get("company_gate_blocked", 0)) + 1
            )
            return None

        self.ctx.metrics["company_gate_advanced"] = (
            int(self.ctx.metrics.get("company_gate_advanced", 0)) + 1
        )

        return {
            "id": str(item.get("id") or "unknown_job"),
            "value": {**dict(result), "job_gate": gate},
            "metadata": {
                **dict(item.get("metadata") or {}),
                "company_type": gate.get("company_type"),
                "gate_confidence": gate.get("confidence"),
            },
        }

    def _job_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("JobGateStage item value must be a job object.")
        return dict(value)
