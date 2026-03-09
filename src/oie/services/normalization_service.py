from __future__ import annotations

from typing import Any, Dict, List

from pipeline.normalize import normalize_jobs
from oie.orchestration.run_context import RunContext


class NormalizationService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def normalize(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = normalize_jobs(jobs)

        self.ctx.metrics["jobs_after_normalize"] = len(normalized)
        self.ctx.metrics["normalize_completed"] = True

        return normalized