from __future__ import annotations

from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.pipeline_stages import PIPELINE_STAGES
from oie.orchestration.run_context import RunContext
from oie.orchestration.stage_artifacts import stage_artifact_paths
from oie.orchestration.stage_checkpoint import load_checkpoint_payload
from oie.orchestration.stage_io import read_json_file, read_jsonl_file


class StageArtifactRepository:
    def __init__(self, ctx: RunContext, run_id: str) -> None:
        self.ctx = ctx
        self.run_id = run_id
        self._configure_ctx_for_run()

    def _configure_ctx_for_run(self) -> None:
        run_dir = f'{self.ctx.paths["runs_base_dir"]}/{self.run_id}'
        self.ctx.paths["run_dir"] = run_dir
        self.ctx.paths["manifest_path"] = f"{run_dir}/manifest.json"
        self.ctx.paths["stage_dirs"] = {
            stage: f"{run_dir}/{index:02d}_{stage}"
            for index, stage in enumerate(PIPELINE_STAGES, start=1)
        }

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
