from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.persistence.context import PersistenceContext
from oie.persistence.repository_provider import RepositoryProvider
from oie.persistence.sqlite import initialize_database
from oie.services.provider_operation_metrics_service import ProviderOperationMetricsService


class PersistenceService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.persistence = PersistenceContext.from_run_context(ctx)
        self.db_path = self.persistence.path or self.ctx.paths.get("db_path") or self.ctx.config.get("database", {}).get("path", "data/oie.db")
        self.ctx.paths["db_path"] = self.db_path
        self.repositories = RepositoryProvider.from_persistence(self.persistence)
        self.run_repository = self.repositories.run_repository
        self.run_metrics_repository = self.repositories.run_metrics_repository
        self.provider_event_repository = self.repositories.provider_event_repository
        self.provider_operation_metrics_repository = self.repositories.provider_operation_metrics_repository
        self.provider_operation_metrics_service = ProviderOperationMetricsService(ctx)
        self.company_repository = self.repositories.company_repository
        self.company_alias_repository = self.repositories.company_alias_repository
        self.domain_repository = self.repositories.domain_repository
        self.company_merge_candidate_repository = self.repositories.company_merge_candidate_repository
        self.job_repository = self.repositories.job_repository
        self.lead_repository = self.repositories.lead_repository
        self.company_score_repository = self.repositories.company_score_repository
        self.company_profile_repository = self.repositories.company_profile_repository

    def initialize(self) -> None:
        if self.persistence.backend == "sqlite":
            initialize_database(self.db_path)
        else:
            from oie.persistence.migrations import run_database_migrations

            run_database_migrations({"database": {"backend": self.persistence.backend, "url": self.persistence.url}})
        self.ctx.metrics["persistence_database_initialized"] = True

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

    def persist_provider_operation_metrics(self, rows: List[Dict[str, Any]] | None = None) -> None:
        if rows is None:
            rows = self.provider_operation_metrics_service.build_rows()
        elif not rows:
            rows = self.provider_operation_metrics_service.build_rows()

        self.provider_operation_metrics_repository.replace_rows(
            run_id=self.ctx.run_id,
            rows=rows,
        )

    def persist_companies(self, companies: List[Dict[str, Any]]) -> None:
        self.company_repository.upsert_companies(companies)
        self.company_alias_repository.replace_aliases(companies)
        self.domain_repository.replace_domains(companies)
        self.company_score_repository.replace_company_scores(self.ctx.run_id, companies)
        self.company_profile_repository.replace_company_profiles(self.ctx.run_id, companies)

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

    def _record_persistence_error(
        self,
        step: str,
        exc: Exception,
    ) -> None:
        metric_key = f"persistence_{step}_failed"
        self.ctx.metrics[metric_key] = True
        self.ctx.metrics["persistence_errors_count"] = int(
            self.ctx.metrics.get("persistence_errors_count", 0) or 0
        ) + 1

        if exc.__class__.__name__ == "OperationalError":
            self.ctx.metrics["persistence_schema_errors_count"] = int(
                self.ctx.metrics.get("persistence_schema_errors_count", 0) or 0
            ) + 1
            if self.persistence.backend == "sqlite":
                self.ctx.metrics["persistence_sqlite_operational_errors_count"] = int(
                    self.ctx.metrics.get("persistence_sqlite_operational_errors_count", 0) or 0
                ) + 1

        self.ctx.add_provider_event(
            provider="persistence",
            event_type="persist_error",
            message=f"{step}: {exc}",
            metadata={
                "step": step,
                "error_type": exc.__class__.__name__,
            },
        )

    def _safe_persist_step(
        self,
        step: str,
        fn,
        *args,
        required: bool = False,
        **kwargs,
    ) -> bool:
        self.ctx.metrics[f"persistence_{step}_attempted"] = True
        try:
            fn(*args, **kwargs)
            self.ctx.metrics[f"persistence_{step}_succeeded"] = True
            return True
        except Exception as exc:
            self.ctx.metrics[f"persistence_{step}_succeeded"] = False
            self._record_persistence_error(step, exc)
            if required:
                raise
            return False

    def persist_run_snapshot(
        self,
        status: str,
        companies: List[Dict[str, Any]] | None = None,
        jobs: List[Dict[str, Any]] | None = None,
        leads: List[Dict[str, Any]] | None = None,
    ) -> None:
        self._safe_persist_step("initialize", self.initialize, required=True)
        self._safe_persist_step("run", self.persist_run, status=status, required=True)
        self._safe_persist_step("metrics", self.persist_metrics)
        self._safe_persist_step("provider_events", self.persist_provider_events)
        self._safe_persist_step(
            "provider_operation_metrics",
            self.persist_provider_operation_metrics,
            self.ctx.provider_state.get("provider_operation_metrics_rows_data"),
        )

        if companies is not None:
            self._safe_persist_step("companies", self.persist_companies, companies)
        if jobs is not None:
            self._safe_persist_step("jobs", self.persist_jobs, jobs)
        if leads is not None:
            self._safe_persist_step("leads", self.persist_leads, leads)
