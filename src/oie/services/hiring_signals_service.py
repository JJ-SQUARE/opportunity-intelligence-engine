from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class HiringSignalsService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def aggregate_by_company(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}

        for job in jobs:
            company = (job.get("company") or "").strip()
            if not company:
                company = "unknown"

            if company not in grouped:
                grouped[company] = {
                    "company": company,
                    "jobs": [],
                    "total_openings": 0,
                    "remote_jobs": 0,
                    "contractor_jobs": 0,
                    "sources": set(),
                    "apply_url": None,
                    "job_url": None,
                    "url": None,
                }

            grouped[company]["jobs"].append(job)
            grouped[company]["total_openings"] += 1

            if job.get("remote_flag"):
                grouped[company]["remote_jobs"] += 1

            if job.get("contractor_flag"):
                grouped[company]["contractor_jobs"] += 1

            if job.get("source"):
                grouped[company]["sources"].add(job["source"])

            if not grouped[company]["apply_url"] and job.get("apply_url"):
                grouped[company]["apply_url"] = job.get("apply_url")

            if not grouped[company]["job_url"] and job.get("job_url"):
                grouped[company]["job_url"] = job.get("job_url")

            if not grouped[company]["url"] and job.get("url"):
                grouped[company]["url"] = job.get("url")

        companies = []
        for company_data in grouped.values():
            company_data["sources"] = sorted(company_data["sources"])
            company_data["remote_friendly"] = company_data["remote_jobs"] > 0
            company_data["contractor_signal"] = company_data["contractor_jobs"] > 0
            companies.append(company_data)

        self.ctx.metrics["companies_detected"] = len(companies)
        self.ctx.metrics["signals_completed"] = True

        return companies
