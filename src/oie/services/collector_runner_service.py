from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

from oie.collectors.registry import CollectorRegistry
from oie.orchestration.run_context import RunContext


class CollectorRunnerService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.registry = CollectorRegistry()

    def register_collectors(self, collectors) -> None:
        for collector in collectors:
            self.registry.register(collector)

    def run_enabled_collectors(self, enabled_names: List[str]) -> List[Dict]:
        collectors = [
            collector
            for collector in self.registry.all()
            if collector.collector_name in enabled_names
        ]

        jobs: List[Dict] = []

        if not collectors:
            self.ctx.metrics["collectors_total_jobs_collected"] = 0
            return jobs

        max_workers = min(len(collectors), 4)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._run_single_collector, collector): collector
                for collector in collectors
            }

            for future in as_completed(futures):
                result = future.result()
                if result:
                    jobs.extend(result)

        self.ctx.metrics["collectors_total_jobs_collected"] = len(jobs)
        return jobs

    def _run_single_collector(self, collector):
        try:
            jobs = collector.collect() or []

            # Compatibilidad con métricas previas
            self.ctx.metrics[f"collector_{collector.collector_name}_jobs_collected"] = len(jobs)

            # Métricas nuevas
            self.ctx.metrics[f"collector_{collector.collector_name}_jobs"] = len(jobs)
            self.ctx.metrics[f"collector_{collector.collector_name}_status"] = "success"

            return jobs

        except Exception as exc:
            self.ctx.metrics[f"collector_{collector.collector_name}_jobs_collected"] = 0
            self.ctx.metrics[f"collector_{collector.collector_name}_jobs"] = 0
            self.ctx.metrics[f"collector_{collector.collector_name}_status"] = "error"
            self.ctx.metrics[f"collector_{collector.collector_name}_error"] = str(exc)
            return []
