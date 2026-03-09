from __future__ import annotations

from typing import Any, Dict

from oie.orchestration.run_context import RunContext
from oie.persistence.repositories import RunMetricsRepository, RunRepository
from oie.persistence.sqlite import initialize_database


class PersistenceService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.db_path = self.ctx.config.get("database", {}).get("path", "data/oie.db")
        self.run_repository = RunRepository(self.db_path)
        self.run_metrics_repository = RunMetricsRepository(self.db_path)

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

    def persist_run_snapshot(self, status: str) -> None:
        self.initialize()
        self.persist_run(status=status)
        self.persist_metrics()
