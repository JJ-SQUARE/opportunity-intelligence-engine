from __future__ import annotations

from typing import Any

from oie.orchestration.collect_jobs_stage import CollectJobsStage
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem
from oie.services.normalization_service import NormalizationService


class NormalizeJobsStage(Stage):
    name = "normalize_jobs"
    order = 2

    def load_input(self) -> list[StageItem]:
        return StageCheckpointManager(CollectJobsStage(self.ctx)).read_output()

    def process_item(self, item: StageItem) -> StageItem:
        job = self._job_from_item(item)
        normalized_jobs = NormalizationService(self.ctx).normalize([job])
        normalized_job = normalized_jobs[0] if normalized_jobs else {}

        return {
            "id": str(item.get("id")),
            "value": normalized_job,
            "metadata": dict(item.get("metadata") or {}),
        }

    def _job_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("NormalizeJobsStage item value must be a job object.")
        return dict(value)

    def _job_id(self, job: dict[str, Any]) -> str:
        for key in ("job_id", "id", "job_url", "apply_url"):
            value = str(job.get(key) or "").strip()
            if value:
                return value
        return "normalized_job"
