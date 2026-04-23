from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Any

from oie.orchestration.run_context import RunContext


class CollectorMetricsService:
    """
    Computes coverage metrics per collector source.
    """

    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def build_metrics(
        self,
        jobs: List[Dict[str, Any]],
        companies: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        source_job_counts = defaultdict(int)
        source_effective_job_counts = defaultdict(int)
        source_company_sets = defaultdict(set)
        source_effective_company_sets = defaultdict(set)

        effective_company_keys = {
            company.get("company_key")
            for company in companies or []
            if company.get("company_key")
        }

        for job in jobs:
            source = job.get("source", "unknown")
            source_job_counts[source] += 1

            company_key = job.get("company_key")
            if company_key:
                source_company_sets[source].add(company_key)

            if company_key and company_key in effective_company_keys:
                source_effective_job_counts[source] += 1
                source_effective_company_sets[source].add(company_key)

        metrics = []

        for source in source_job_counts:

            jobs_count = source_job_counts[source]
            companies_count = len(source_company_sets[source])
            effective_jobs_count = source_effective_job_counts[source]
            effective_companies_count = len(source_effective_company_sets[source])

            metrics.append(
                {
                    "source": source,
                    "jobs_collected": jobs_count,
                    "jobs_effective": effective_jobs_count,
                    "unique_companies": companies_count,
                    "effective_companies": effective_companies_count,
                    "jobs_per_company": round(
                        jobs_count / companies_count, 2
                    )
                    if companies_count
                    else 0,
                    "effective_jobs_per_company": round(
                        effective_jobs_count / effective_companies_count, 2
                    )
                    if effective_companies_count
                    else 0,
                    "job_effectiveness_rate": round(
                        effective_jobs_count / jobs_count, 4
                    )
                    if jobs_count
                    else 0,
                }
            )

        metrics.sort(
            key=lambda x: (x["jobs_effective"], x["jobs_collected"]),
            reverse=True,
        )

        self.ctx.metrics["collector_metrics_rows"] = len(metrics)
        return metrics
