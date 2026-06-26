from __future__ import annotations

from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint import build_initial_checkpoint, read_checkpoint_file
from oie.orchestration.stage_io import append_jsonl_item, write_json_file
from oie.orchestration.stage_item import StageItem
from oie.orchestration.stage_metrics import StageMetrics, build_stage_metrics
from oie.orchestration.stage_state import StageState


class StageCheckpointManager:
    def __init__(self, stage: Stage) -> None:
        self.stage = stage

    def initial_checkpoint(self, status: str = "running") -> StageState:
        return build_initial_checkpoint(self.stage.ctx, self.stage, status)

    def read_checkpoint(self) -> StageState | None:
        paths = self.stage.artifact_paths()
        return read_checkpoint_file(paths["checkpoint"])

    def write_checkpoint(self, checkpoint: StageState) -> None:
        paths = self.stage.artifact_paths()
        paths["stage_dir"].mkdir(parents=True, exist_ok=True)
        write_json_file(paths["checkpoint"], checkpoint)

    def write_metrics(self, checkpoint: StageState) -> StageMetrics:
        paths = self.stage.artifact_paths()
        metrics = build_stage_metrics(checkpoint)
        write_json_file(paths["metrics"], metrics)
        return metrics

    def append_output(self, item: StageItem) -> None:
        paths = self.stage.artifact_paths()
        paths["stage_dir"].mkdir(parents=True, exist_ok=True)
        append_jsonl_item(paths["output"], item)
