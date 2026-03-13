from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.persistence.repositories import (
    CompanyAliasRepository,
    CompanyMergeCandidateRepository,
    CompanyRepository,
    CompanyScoreRepository,
    DomainRepository,
    JobRepository,
    LeadRepository,
    ProviderEventRepository,
    RunMetricsRepository,
    RunRepository,
)
from oie.persistence.sqlite import initialize_database


class PersistenceService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.db_path = self.ctx.paths.get("db_path") or self.ctx.config.get("database", {}).get("path", "data/oie.db")
        self.run_repository = RunRepository(self.db_path)
        self.run_metrics_repository = RunMetricsRepository(self.db_path)
        self.provider_event_repository = ProviderEventRepository(self.db_path)
        self.company_repository = CompanyRepository(self.db_path)
        self.company_alias_repository = CompanyAliasRepository(self.db_path)
        self.domain_repository = DomainRepository(self.db_path)
        self.company_merge_candidate_repository = CompanyMergeCandidateRepository(self.db_path)
        self.job_repository = JobRepository(self.db_path)
        self.lead_repository = LeadRepository(self.db_path)
        self.company_score_repository = CompanyScoreRepository(self.db_path)

    def initialize(self) -> None:
        initialize_database(self.db_path)

    def persist_run(self, status: str) -> None:
        self.run_repository.upsert_run(
            run_id=self.ctx.run_id,
            run_date=self.ctx.run_date,
            status=status,
            mode=self.ctx.mode,
        )

    def persist_metrics(self) -> None:
        self.run_metrics_repository.replace_metrics(
            run_id=self.ctx.run_id,
            metrics=self.ctx.metrics,
        )

    def persist_provider_events(self) -> None:
        self.provider_event_repository.replace_events(
            run_id=self.ctx.run_id,
            provider_events=self.ctx.provider_events,
        )

    def persist_companies(self, companies: List[Dict[str, Any]]) -> None:
        self.company_repository.upsert_companies(companies)
        self.company_alias_repository.replace_aliases(companies)
        self.domain_repository.replace_domains(companies)
        self.company_score_repository.replace_company_scores(self.ctx.run_id, companies)

        merge_candidates = self.ctx.provider_state.get("company_merge_candidates", []) or []
        self.company_merge_candidate_repository.replace_merge_candidates(
            run_id=self.ctx.run_id,
            candidates=merge_candidates,
        )

    def persist_jobs(self, jobs: List[Dict[str, Any]]) -> None:
        self.job_repository.replace_jobs(
            run_id=self.ctx.run_id,
            run_date=self.ctx.run_date,
            jobs=jobs,
        )

    def persist_leads(self, leads: List[Dict[str, Any]]) -> None:
        self.lead_repository.replace_leads(
            run_id=self.ctx.run_id,
            run_date=self.ctx.run_date,
            leads=leads,
        )

    def persist_run_snapshot(
        self,
        status: str,
        companies: List[Dict[str, Any]] | None = None,
        jobs: List[Dict[str, Any]] | None = None,
        leads: List[Dict[str, Any]] | None = None,
    ) -> None:
        self.initialize()
        self.persist_run(status=status)
        self.persist_metrics()
        self.persist_provider_events()

        if companies is not None:
            self.persist_companies(companies)
        if jobs is not None:
            self.persist_jobs(jobs)
        if leads is not None:
            self.persist_leads(leads)
