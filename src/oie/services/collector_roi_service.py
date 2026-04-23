from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class CollectorROIService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def build_roi_metrics(
        self,
        unique_jobs: List[Dict[str, Any]],
        duplicate_jobs: List[Dict[str, Any]],
        companies: List[Dict[str, Any]],
        leads: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        source_unique_jobs = defaultdict(int)
        source_effective_unique_jobs = defaultdict(int)
        source_duplicates = defaultdict(int)
        source_new_companies = defaultdict(int)
        source_leads = defaultdict(int)
        company_first_source: Dict[str, str] = {}

        effective_company_keys = {
            company.get("company_key")
            for company in companies or []
            if company.get("company_key")
        }

        for job in unique_jobs:
            source = job.get("source", "unknown")
            source_unique_jobs[source] += 1

            company_key = job.get("company_key")
            if company_key and company_key in effective_company_keys:
                source_effective_unique_jobs[source] += 1

            if company_key and company_key in effective_company_keys and company_key not in company_first_source:
                company_first_source[company_key] = source
                source_new_companies[source] += 1

        for job in duplicate_jobs:
            source = job.get("source", "unknown")
            source_duplicates[source] += 1

        for lead in leads:
            company_key = lead.get("company_key")
            if not company_key:
                continue
            source = company_first_source.get(company_key, "unknown")
            source_leads[source] += 1

        all_sources = (
            set(source_unique_jobs.keys())
            | set(source_duplicates.keys())
            | set(source_new_companies.keys())
            | set(source_leads.keys())
        )

        rows: List[Dict[str, Any]] = []
        for source in all_sources:
            unique_jobs_count = source_unique_jobs[source]
            effective_unique_jobs_count = source_effective_unique_jobs[source]
            duplicate_jobs_count = source_duplicates[source]
            new_companies_count = source_new_companies[source]
            leads_generated_count = source_leads[source]

            utility_score = (
                effective_unique_jobs_count * 1.0
                + new_companies_count * 3.0
                + leads_generated_count * 2.0
                - duplicate_jobs_count * 0.5
            )

            rows.append(
                {
                    "source": source,
                    "unique_jobs": unique_jobs_count,
                    "effective_unique_jobs": effective_unique_jobs_count,
                    "duplicate_jobs": duplicate_jobs_count,
                    "new_companies": new_companies_count,
                    "leads_generated": leads_generated_count,
                    "utility_score": round(utility_score, 2),
                }
            )

        rows.sort(
            key=lambda row: (
                row["utility_score"],
                row["new_companies"],
                row["effective_unique_jobs"],
                row["unique_jobs"],
            ),
            reverse=True,
        )

        self.ctx.metrics["collector_roi_rows"] = len(rows)
        return rows
