from __future__ import annotations

from oie.orchestration.run_context import RunContext
from oie.persistence.repositories import ProviderEventRepository, RunMetricsRepository, RunRepository
from oie.persistence.sqlite import initialize_database


class PersistenceService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.db_path = self.ctx.config.get("database", {}).get("path", "data/oie.db")
        self.run_repository = RunRepository(self.db_path)
        self.run_metrics_repository = RunMetricsRepository(self.db_path)
        self.provider_event_repository = ProviderEventRepository(self.db_path)

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

    def persist_run_snapshot(self, status: str) -> None:
        self.initialize()
        self.persist_run(status=status)
        self.persist_metrics()
        self.persist_provider_events()
