from __future__ import annotations

from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.run_context import RunContext
from oie.orchestration.run_manifest import list_run_summaries, read_run_status


class RunRepository:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def list_summaries(self) -> list[JSONPayload]:
        return list_run_summaries(self.ctx)

    def read_status(self, run_id: str) -> JSONPayload | None:
        return read_run_status(self.ctx, run_id)
