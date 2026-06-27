from __future__ import annotations

from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.run_context import RunContext
from oie.orchestration.run_manifest import list_run_summaries, read_run_detail, read_run_errors, read_run_metrics_summary, read_run_stage_status, read_run_stage_statuses, read_run_status


class RunRepository:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    @classmethod
    def create(cls) -> "RunRepository":
        return cls(RunContext.create())

    def list_summaries(self) -> list[JSONPayload]:
        return list_run_summaries(self.ctx)

    def read_status(self, run_id: str) -> JSONPayload | None:
        return read_run_status(self.ctx, run_id)

    def read_stages(self, run_id: str) -> list[JSONPayload] | None:
        return read_run_stage_statuses(self.ctx, run_id)

    def read_stage(self, run_id: str, stage_name: str) -> JSONPayload | None:
        return read_run_stage_status(self.ctx, run_id, stage_name)

    def read_errors(self, run_id: str) -> list[JSONPayload] | None:
        return read_run_errors(self.ctx, run_id)

    def read_metrics_summary(self, run_id: str) -> JSONPayload | None:
        return read_run_metrics_summary(self.ctx, run_id)

    def read_detail(self, run_id: str) -> JSONPayload | None:
        return read_run_detail(self.ctx, run_id)
