from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.services.job_text_service import description_looks_contaminated


class HiringSignalsService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def _description_priority(self, job: Dict[str, Any]) -> int:
        source = str(job.get("source") or "").strip().lower()
        description = " ".join(str(job.get("description") or "").split()).strip()

        if not description:
            return 0

        if description_looks_contaminated(job):
            return 0

        if source in {"google_jobs", "greenhouse", "lever", "workable", "direct", "company_site"}:
            return 3

        if source == "linkedin_serpapi":
            return 1

        return 2

    def _should_replace_description(
        self,
        current_job: Dict[str, Any] | None,
        new_job: Dict[str, Any],
    ) -> bool:
        if current_job is None:
            return True

        current_priority = self._description_priority(current_job)
        new_priority = self._description_priority(new_job)

        if new_priority != current_priority:
            return new_priority > current_priority

        current_len = len(" ".join(str(current_job.get("description") or "").split()).strip())
        new_len = len(" ".join(str(new_job.get("description") or "").split()).strip())
        return new_len > current_len

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
                    "description_source": None,
                    "source_meta": {},
                    "ai_company_gate_company_type": None,
                    "ai_company_gate_relevance": None,
                    "ai_company_gate_should_advance": True,
                    "ai_company_gate_reason": None,
                    "ai_company_gate_domain_guess": None,
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

            current_description_job = None
            if grouped[company]["description"]:
                current_description_job = {
                    "description": grouped[company]["description"],
                    "source": grouped[company]["description_source"],
                }

            if job.get("description") and self._should_replace_description(current_description_job, job):
                grouped[company]["description"] = job.get("description")
                grouped[company]["description_source"] = job.get("source")

            if not grouped[company]["source_meta"] and job.get("source_meta"):
                grouped[company]["source_meta"] = job.get("source_meta") or {}

            if job.get("ai_company_gate_company_type") and not grouped[company]["ai_company_gate_company_type"]:
                grouped[company]["ai_company_gate_company_type"] = job.get("ai_company_gate_company_type")
            if job.get("ai_company_gate_relevance") and not grouped[company]["ai_company_gate_relevance"]:
                grouped[company]["ai_company_gate_relevance"] = job.get("ai_company_gate_relevance")
            if job.get("ai_company_gate_domain_guess") and not grouped[company]["ai_company_gate_domain_guess"]:
                grouped[company]["ai_company_gate_domain_guess"] = job.get("ai_company_gate_domain_guess")
            if job.get("ai_company_gate_should_advance") is False:
                grouped[company]["ai_company_gate_should_advance"] = False
                grouped[company]["ai_company_gate_reason"] = job.get("ai_company_gate_reason")

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
