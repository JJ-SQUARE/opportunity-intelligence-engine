from __future__ import annotations

from typing import TypeAlias

from oie.orchestration.run_context import RunContext
from oie.orchestration.run_manifest import update_stage_status
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_metrics import StageMetrics
from oie.orchestration.stage_result import StageResult
from oie.orchestration.stage_timing import start_timer
from oie.orchestration.stage_io import read_jsonl_file
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_item import StageItem
from oie.orchestration.stage_state import StageState


StageClass: TypeAlias = type[Stage]


class StageRunner:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def initial_checkpoint(self, stage: Stage, status: str = "running") -> StageState:
        return StageCheckpointManager(stage).initial_checkpoint(status)

    def write_checkpoint(self, stage: Stage, checkpoint: StageState) -> None:
        StageCheckpointManager(stage).write_checkpoint(checkpoint)

    def write_metrics(self, stage: Stage, checkpoint: StageState) -> StageMetrics:
        return StageCheckpointManager(stage).write_metrics(checkpoint)

    def append_output(self, stage: Stage, item: StageItem) -> None:
        StageCheckpointManager(stage).append_output(item)

    def build_result(self, checkpoint: StageState, metrics: StageMetrics) -> StageResult:
        return {
            "run_id": checkpoint["run_id"],
            "stage": checkpoint["stage"],
            "status": checkpoint["status"],
            "checkpoint": checkpoint,
            "metrics": metrics,
        }

    def read_output(self, stage: Stage) -> list[StageItem]:
        paths = stage.artifact_paths()
        return read_jsonl_file(paths["output"])

    def read_checkpoint(self, stage: Stage) -> StageState | None:
        return StageCheckpointManager(stage).read_checkpoint()

    def run_stage(self, stage_cls: StageClass) -> StageState:
        stage = stage_cls(self.ctx)
        checkpoint_manager = StageCheckpointManager(stage)
        stage.ensure_stage_dir()
        update_stage_status(self.ctx, stage.name, "running")
        inputs = list(stage.load_input())
        checkpoint, start_index = checkpoint_manager.prepare_checkpoint(len(inputs))
        start_time = start_timer()

        try:
            for index, item in enumerate(inputs[start_index:], start=start_index):
                output_item = stage.process_item(item)
                self.append_output(stage, output_item)
                checkpoint_manager.record_processed_item(checkpoint, index, output_item)
                self.write_checkpoint(stage, checkpoint)
        except Exception as exc:
            failure_status = checkpoint_manager.record_stage_failure(checkpoint, exc, start_time)
            self.write_checkpoint(stage, checkpoint)
            self.write_metrics(stage, checkpoint)
            update_stage_status(self.ctx, stage.name, failure_status)
            raise

        checkpoint_manager.record_stage_completion(checkpoint, start_time)
        self.write_checkpoint(stage, checkpoint)
        self.write_metrics(stage, checkpoint)
        update_stage_status(self.ctx, stage.name, "completed")
        return checkpoint
