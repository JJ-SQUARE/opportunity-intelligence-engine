from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class CollectorContributionService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def build_contribution_metrics(
        self,
        jobs: List[Dict[str, Any]],
        companies: List[Dict[str, Any]],
        leads: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        company_first_source: Dict[str, str] = {}
        source_jobs = defaultdict(int)
        source_effective_jobs = defaultdict(int)
        source_unique_jobs = defaultdict(set)
        source_companies = defaultdict(set)
        source_effective_companies = defaultdict(set)
        source_new_companies = defaultdict(int)
        source_leads = defaultdict(int)

        effective_company_keys = {
            company.get("company_key")
            for company in companies or []
            if company.get("company_key")
        }

        for job in jobs:
            source = job.get("source", "unknown")
            company_key = job.get("company_key")
            job_key = job.get("job_key") or job.get("job_url") or job.get("apply_url") or str(job)

            source_jobs[source] += 1
            source_unique_jobs[source].add(job_key)

            if company_key:
                source_companies[source].add(company_key)

            if company_key and company_key in effective_company_keys:
                source_effective_jobs[source] += 1
                source_effective_companies[source].add(company_key)
                if company_key not in company_first_source:
                    company_first_source[company_key] = source
                    source_new_companies[source] += 1

        company_source_lookup: Dict[str, str] = {}
        for job in jobs:
            company_key = job.get("company_key")
            source = job.get("source", "unknown")
            if company_key and company_key not in company_source_lookup:
                company_source_lookup[company_key] = source

        for lead in leads:
            company_key = lead.get("company_key")
            if not company_key:
                continue
            source = company_source_lookup.get(company_key, "unknown")
            source_leads[source] += 1

        all_sources = set(source_jobs.keys()) | set(source_leads.keys()) | set(source_new_companies.keys())

        rows: List[Dict[str, Any]] = []
        for source in all_sources:
            jobs_collected = source_jobs[source]
            effective_jobs = source_effective_jobs[source]
            unique_jobs = len(source_unique_jobs[source])
            unique_companies = len(source_companies[source])
            effective_companies = len(source_effective_companies[source])
            new_companies = source_new_companies[source]
            leads_generated = source_leads[source]

            contribution_score = (
                effective_jobs * 1.0
                + new_companies * 3.0
                + leads_generated * 2.0
            )

            rows.append(
                {
                    "source": source,
                    "jobs_collected": jobs_collected,
                    "jobs_effective": effective_jobs,
                    "unique_jobs": unique_jobs,
                    "unique_companies": unique_companies,
                    "effective_companies": effective_companies,
                    "new_companies": new_companies,
                    "leads_generated": leads_generated,
                    "contribution_score": round(contribution_score, 2),
                }
            )

        rows.sort(
            key=lambda row: (
                row["contribution_score"],
                row["new_companies"],
                row["jobs_effective"],
                row["unique_jobs"],
            ),
            reverse=True,
        )

        self.ctx.metrics["collector_contribution_rows"] = len(rows)
        return rows
