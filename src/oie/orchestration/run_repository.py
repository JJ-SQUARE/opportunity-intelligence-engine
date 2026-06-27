from __future__ import annotations

from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.run_context import RunContext
from oie.orchestration.run_manifest import list_run_manifests, read_run_manifest


class RunRepository:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    @classmethod
    def create(cls) -> "RunRepository":
        return cls(RunContext.create())

    def list_summaries(self) -> list[JSONPayload]:
        return [
            {
                "run_id": manifest["run_id"],
                "status": manifest["status"],
                "current_stage": manifest["current_stage"],
                "created_at": manifest["created_at"],
                "updated_at": manifest["updated_at"],
            }
            for manifest in list_run_manifests(self.ctx)
        ]

    def read_status(self, run_id: str) -> JSONPayload | None:
        manifest = read_run_manifest(self.ctx, run_id)
        if manifest is None:
            return None
        return {
            "run_id": manifest["run_id"],
            "status": manifest["status"],
            "current_stage": manifest["current_stage"],
        }

    def read_stages(self, run_id: str) -> list[JSONPayload] | None:
        manifest = read_run_manifest(self.ctx, run_id)
        if manifest is None:
            return None
        return [
            {"stage": stage_name, "status": status}
            for stage_name, status in manifest.get("stages", {}).items()
        ]

    def read_stage(self, run_id: str, stage_name: str) -> JSONPayload | None:
        manifest = read_run_manifest(self.ctx, run_id)
        if manifest is None:
            return None
        stages = manifest.get("stages", {})
        if stage_name not in stages:
            return None
        return {"stage": stage_name, "status": stages[stage_name]}

    def read_errors(self, run_id: str) -> list[JSONPayload] | None:
        manifest = read_run_manifest(self.ctx, run_id)
        if manifest is None:
            return None
        return list(manifest.get("errors", []))

    def read_metrics_summary(self, run_id: str) -> JSONPayload | None:
        manifest = read_run_manifest(self.ctx, run_id)
        if manifest is None:
            return None
        stages = manifest.get("stages", {})
        return {
            "run_id": manifest["run_id"],
            "stage_count": len(stages),
            "error_count": len(manifest.get("errors", [])),
            "status_counts": {
                status: list(stages.values()).count(status)
                for status in sorted(set(stages.values()))
            },
        }

    def read_detail(self, run_id: str) -> JSONPayload | None:
        manifest = read_run_manifest(self.ctx, run_id)
        if manifest is None:
            return None
        return dict(manifest)
