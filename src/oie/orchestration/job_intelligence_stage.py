from __future__ import annotations

from typing import Any

from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem
from oie.services.job_intelligence_service import JobIntelligenceService
from oie.services.provider_control_service import ProviderControlService


class JobIntelligenceStage(Stage):
    name = "job_intelligence"
    order = 5

    def load_input(self) -> list[StageItem]:
        from oie.orchestration.urgency_gate_stage import UrgencyGateStage
        return StageCheckpointManager(UrgencyGateStage(self.ctx)).read_output()

    def process_item(self, item: StageItem) -> StageItem:
        job = self._job_from_item(item)
        provider_control_service = ProviderControlService(self.ctx)
        provider_control_service.initialize()
        provider_control_service.sync_budget_metrics()

        enriched_jobs = JobIntelligenceService(
            self.ctx,
            provider_control_service,
        ).enrich_jobs([job])
        enriched_job = enriched_jobs[0] if enriched_jobs else {}

        return {
            "id": str(item.get("id") or "unknown_job"),
            "value": enriched_job,
            "metadata": dict(item.get("metadata") or {}),
        }

    def _job_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("JobIntelligenceStage item value must be a job object.")
        return dict(value)

    def _job_id(self, job: dict[str, Any]) -> str:
        for key in ("job_id", "id", "job_url", "apply_url"):
            value = str(job.get(key) or "").strip()
            if value:
                return value
        return "job_intelligence_job"
