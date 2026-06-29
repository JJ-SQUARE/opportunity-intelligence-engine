from __future__ import annotations

from typing import Any, Dict, List, Tuple

from oie.orchestration.run_context import RunContext
from oie.persistence.context import PersistenceContext
from oie.persistence.repository_provider import RepositoryProvider
from oie.services.master_data_service import MasterDataService


class MasterDedupService:
    def __init__(
        self,
        ctx: RunContext,
        repositories: RepositoryProvider | None = None,
    ) -> None:
        self.ctx = ctx
        self.master_data_service = MasterDataService(ctx)
        self.persistence = PersistenceContext.from_run_context(ctx)
        self.repositories = repositories or RepositoryProvider.from_persistence(self.persistence)
        self.job_repository = self.repositories.job_repository
        self.lead_repository = self.repositories.lead_repository

    def _job_dedupe_key(self, job: Dict[str, Any]) -> Tuple[str, str]:
        return ("job_fingerprint", self.job_repository._build_job_fingerprint(job))

    def _lead_dedupe_key(self, lead: Dict[str, Any]) -> Tuple[str, str]:
        return ("lead_fingerprint", self.lead_repository._build_lead_fingerprint(lead))

    def dedupe_jobs_against_master(
        self,
        jobs: List[Dict[str, Any]],
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        master_rows = self.master_data_service.read_master_rows("jobs")
        existing_keys = {self._job_dedupe_key(row) for row in master_rows}

        unique_jobs: List[Dict[str, Any]] = []
        duplicates: List[Dict[str, Any]] = []

        for job in jobs:
            key = self._job_dedupe_key(job)
            if key in existing_keys:
                duplicates.append(job)
                continue
            existing_keys.add(key)
            unique_jobs.append(job)

        self.ctx.metrics["master_jobs_duplicates_detected"] = len(duplicates)
        self.ctx.metrics["master_jobs_unique_to_append"] = len(unique_jobs)
        return unique_jobs, duplicates

    def dedupe_leads_against_master(
        self,
        leads: List[Dict[str, Any]],
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        master_rows = self.master_data_service.read_master_rows("leads")
        existing_keys = {self._lead_dedupe_key(row) for row in master_rows}

        unique_leads: List[Dict[str, Any]] = []
        duplicates: List[Dict[str, Any]] = []

        for lead in leads:
            key = self._lead_dedupe_key(lead)
            if key in existing_keys:
                duplicates.append(lead)
                continue
            existing_keys.add(key)
            unique_leads.append(lead)

        self.ctx.metrics["master_leads_duplicates_detected"] = len(duplicates)
        self.ctx.metrics["master_leads_unique_to_append"] = len(unique_leads)
        return unique_leads, duplicates

    def build_suspected_duplicates_report(
        self,
        jobs_duplicates: List[Dict[str, Any]],
        leads_duplicates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        report: List[Dict[str, Any]] = []

        for job in jobs_duplicates:
            report.append(
                {
                    "entity_type": "job",
                    "company": job.get("company", ""),
                    "primary_value": job.get("job_url") or job.get("apply_url") or job.get("title", ""),
                    "reason": "duplicate_against_master",
                    "run_id": self.ctx.run_id,
                    "run_date": self.ctx.run_date,
                }
            )

        for lead in leads_duplicates:
            report.append(
                {
                    "entity_type": "lead",
                    "company": lead.get("company_key", ""),
                    "primary_value": lead.get("email") or lead.get("contact_name", ""),
                    "reason": "duplicate_against_master",
                    "run_id": self.ctx.run_id,
                    "run_date": self.ctx.run_date,
                }
            )

        self.ctx.metrics["suspected_duplicates_report_count"] = len(report)
        return report
