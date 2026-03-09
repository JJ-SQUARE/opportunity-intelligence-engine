from __future__ import annotations

from typing import Any, Dict, List

from oie.collectors.base import BaseJobCollector
from oie.collectors.registry import CollectorRegistry
from oie.orchestration.run_context import RunContext


class CollectorRunnerService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.registry = CollectorRegistry()

    def register_collectors(self, collectors: List[BaseJobCollector]) -> None:
        for collector in collectors:
            self.registry.register(collector)

    def run_enabled_collectors(self, enabled_names: List[str] | None = None) -> List[Dict[str, Any]]:
        collected_jobs: List[Dict[str, Any]] = []
        collectors = self.registry.enabled(enabled_names)

        self.ctx.metrics["collectors_enabled_count"] = len(collectors)
        self.ctx.metrics["collectors_enabled_names"] = ",".join(
            collector.collector_name for collector in collectors
        )

        for collector in collectors:
            jobs = collector.collect()
            self.ctx.metrics[f"collector_{collector.collector_name}_jobs_collected"] = len(jobs)
            collected_jobs.extend(jobs)

        self.ctx.metrics["collectors_total_jobs_collected"] = len(collected_jobs)
        return collected_jobs
