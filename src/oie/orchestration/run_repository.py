from __future__ import annotations

from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.run_context import RunContext
from oie.orchestration.run_manifest import build_run_detail, build_run_errors, build_run_metrics_summary, build_run_status, build_run_summary, build_stage_status, build_stage_statuses, list_run_manifests, read_run_manifest


class RunRepository:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    @classmethod
    def create(cls) -> "RunRepository":
        return cls(RunContext.create())

    def list_summaries(self) -> list[JSONPayload]:
        return [build_run_summary(manifest) for manifest in list_run_manifests(self.ctx)]

    def read_status(self, run_id: str) -> JSONPayload | None:
        manifest = read_run_manifest(self.ctx, run_id)
        if manifest is None:
            return None
        return build_run_status(manifest)

    def read_stages(self, run_id: str) -> list[JSONPayload] | None:
        manifest = read_run_manifest(self.ctx, run_id)
        if manifest is None:
            return None
        return build_stage_statuses(manifest)

    def read_stage(self, run_id: str, stage_name: str) -> JSONPayload | None:
        manifest = read_run_manifest(self.ctx, run_id)
        if manifest is None:
            return None
        return build_stage_status(manifest, stage_name)

    def read_errors(self, run_id: str) -> list[JSONPayload] | None:
        manifest = read_run_manifest(self.ctx, run_id)
        if manifest is None:
            return None
        return build_run_errors(manifest)

    def read_metrics_summary(self, run_id: str) -> JSONPayload | None:
        manifest = read_run_manifest(self.ctx, run_id)
        if manifest is None:
            return None
        return build_run_metrics_summary(manifest)

    def read_detail(self, run_id: str) -> JSONPayload | None:
        manifest = read_run_manifest(self.ctx, run_id)
        if manifest is None:
            return None
        return build_run_detail(manifest)
