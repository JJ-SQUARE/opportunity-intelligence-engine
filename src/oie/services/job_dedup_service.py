from __future__ import annotations

from typing import Any, Dict, List

from pipeline.dedupe import dedupe_jobs
from oie.orchestration.run_context import RunContext


class JobDedupService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def dedupe(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        before = len(jobs)
        deduped = dedupe_jobs(jobs)
        after = len(deduped)

        self.ctx.metrics["jobs_before_dedupe"] = before
        self.ctx.metrics["jobs_after_dedupe"] = after
        self.ctx.metrics["jobs_deduplicated"] = max(before - after, 0)
        self.ctx.metrics["dedupe_completed"] = True

        return deduped