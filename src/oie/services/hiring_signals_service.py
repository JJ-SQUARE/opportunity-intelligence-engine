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
                    "title": None,
                    "description": None,
                    "source_meta": {},
                }

            grouped[company]["jobs"].append(job)
            grouped[company]["total_openings"] += 1

            is_remote = bool(job.get("is_remote") or job.get("remote_flag"))
            is_contractor = bool(job.get("is_contractor") or job.get("contractor_flag"))

            if is_remote:
                grouped[company]["remote_jobs"] += 1

            if is_contractor:
                grouped[company]["contractor_jobs"] += 1

            if job.get("source"):
                grouped[company]["sources"].add(job["source"])

            if not grouped[company]["apply_url"] and job.get("apply_url"):
                grouped[company]["apply_url"] = job.get("apply_url")

            if not grouped[company]["job_url"] and job.get("job_url"):
                grouped[company]["job_url"] = job.get("job_url")

            if not grouped[company]["url"] and job.get("url"):
                grouped[company]["url"] = job.get("url")

            if not grouped[company]["title"] and job.get("title"):
                grouped[company]["title"] = job.get("title")

            if not grouped[company]["description"] and job.get("description"):
                grouped[company]["description"] = job.get("description")

            if not grouped[company]["source_meta"] and job.get("source_meta"):
                grouped[company]["source_meta"] = job.get("source_meta") or {}

        companies = []
        for company_data in grouped.values():
            total_openings = int(company_data["total_openings"] or 0)
            remote_jobs = int(company_data["remote_jobs"] or 0)
            contractor_jobs = int(company_data["contractor_jobs"] or 0)

            company_data["sources"] = sorted(company_data["sources"])
            company_data["remote_friendly"] = remote_jobs > 0
            company_data["contractor_signal"] = contractor_jobs > 0
            company_data["remote_ratio"] = (remote_jobs / total_openings) if total_openings else 0.0
            company_data["contractor_ratio"] = (contractor_jobs / total_openings) if total_openings else 0.0
            company_data["multi_source_signal"] = len(company_data["sources"]) > 1

            companies.append(company_data)

        self.ctx.metrics["companies_detected"] = len(companies)
        self.ctx.metrics["signals_completed"] = True

        return companies
