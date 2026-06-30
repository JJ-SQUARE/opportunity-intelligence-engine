from __future__ import annotations

from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.pipeline_stages import PIPELINE_STAGES
from oie.orchestration.run_context import RunContext
from oie.orchestration.run_storage_resolver import configure_ctx_for_run_storage
from oie.orchestration.stage_artifacts import stage_artifact_paths
from oie.orchestration.stage_checkpoint import load_checkpoint_payload
from oie.orchestration.stage_io import read_json_file, read_jsonl_file


class StageArtifactRepository:
    def __init__(self, ctx: RunContext, run_id: str) -> None:
        self.ctx = ctx
        self.run_id = run_id
        self._configure_ctx_for_run()

    def _configure_ctx_for_run(self) -> None:
        configure_ctx_for_run_storage(self.ctx, self.run_id)

    def read_checkpoint(self, stage_name: str) -> JSONPayload | None:
        checkpoint = read_json_file(stage_artifact_paths(self.ctx, stage_name)["checkpoint"])
        if checkpoint is None:
            return None
        return load_checkpoint_payload(checkpoint)

    def read_metrics(self, stage_name: str) -> JSONPayload | None:
        return read_json_file(stage_artifact_paths(self.ctx, stage_name)["metrics"])

    def read_output(self, stage_name: str) -> list[JSONPayload] | None:
        output_path = stage_artifact_paths(self.ctx, stage_name)["output"]
        if not output_path.exists():
            return None
        return read_jsonl_file(output_path)

    def read_errors(self, stage_name: str) -> list[JSONPayload] | None:
        checkpoint = read_json_file(stage_artifact_paths(self.ctx, stage_name)["checkpoint"])
        if checkpoint is None:
            return None
        return list(checkpoint.get("errors", []))


    def read_summary(self, stage_name: str) -> JSONPayload:
        paths = stage_artifact_paths(self.ctx, stage_name)
        checkpoint = self.read_checkpoint(stage_name)
        metrics = self.read_metrics(stage_name)
        output = self.read_output(stage_name)

        return {
            "run_id": self.run_id,
            "stage": stage_name,
            "has_checkpoint": checkpoint is not None,
            "has_metrics": metrics is not None,
            "has_output": output is not None,
            "status": (checkpoint or metrics or {}).get("status"),
            "input_count": (checkpoint or metrics or {}).get("input_count", 0),
            "processed_count": (checkpoint or metrics or {}).get("processed_count", 0),
            "output_count": len(output) if output is not None else 0,
            "error_count": len((checkpoint or {}).get("errors", [])),
            "artifact_paths": {
                "stage_dir": str(paths["stage_dir"]),
                "checkpoint": str(paths["checkpoint"]),
                "metrics": str(paths["metrics"]),
                "output": str(paths["output"]),
            },
        }


    def read_catalog(self) -> JSONPayload:
        return {
            "run_id": self.run_id,
            "artifacts": [
                self.read_summary(stage_name)
                for stage_name in PIPELINE_STAGES
            ],
        }
