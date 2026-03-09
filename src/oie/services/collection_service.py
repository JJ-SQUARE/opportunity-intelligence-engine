
from typing import Any, Dict, List

from collectors.run_collectors import run_collectors as run_enabled_collectors
from oie.orchestration.run_context import RunContext
from oie.models.job_record import JobRecord


class CollectionService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def collect(self) -> List[Dict[str, Any]]:
        jobs = run_enabled_collectors(self.ctx.config)

        self.ctx.metrics["jobs_collected_raw"] = len(jobs)
        self.ctx.metrics["collect_completed"] = True

        return jobs

    def collect_as_records(self) -> List[JobRecord]:
        jobs = self.collect()
        records: List[JobRecord] = []

        for job in jobs:
            records.append(
                JobRecord(
                    title=job.get("title") or "",
                    company=job.get("company") or "",
                    location=job.get("location"),
                    job_url=job.get("job_url"),
                    apply_url=job.get("apply_url"),
                    description=job.get("description"),
                    source=job.get("source"),
                    detected_at=job.get("detected_at"),
                )
            )

        return records