from __future__ import annotations

from typing import Any

from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_item import StageItem
from oie.services.collection_service import CollectionService


class CollectJobsStage(Stage):
    name = "collect_jobs"
    order = 1

    def load_input(self) -> list[StageItem]:
        jobs = CollectionService(self.ctx).collect()
        return [
            {
                "id": self._job_id(job, index),
                "value": job,
                "metadata": {
                    "source": job.get("source"),
                    "job_url": job.get("job_url"),
                    "apply_url": job.get("apply_url"),
                },
            }
            for index, job in enumerate(jobs, start=1)
        ]

    def process_item(self, item: StageItem) -> StageItem:
        return item

    def _job_id(self, job: dict[str, Any], index: int) -> str:
        for key in ("job_id", "id", "job_url", "apply_url"):
            value = str(job.get(key) or "").strip()
            if value:
                return value
        return f"collected_job_{index}"
