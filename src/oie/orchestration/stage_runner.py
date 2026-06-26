from __future__ import annotations

from typing import TypeAlias

from oie.orchestration.run_context import RunContext
from oie.orchestration.run_manifest import update_stage_status
from oie.orchestration.stage_checkpoint import build_initial_checkpoint, merge_previous_checkpoint, next_start_index, read_checkpoint_file, record_processed_item, record_stage_completion, record_stage_failure
from oie.orchestration.stage_metrics import StageMetrics, build_stage_metrics
from oie.orchestration.stage_result import StageResult
from oie.orchestration.stage_timing import start_timer
from oie.orchestration.stage_io import append_jsonl_item, read_jsonl_file, write_json_file
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_item import StageItem
from oie.orchestration.stage_state import StageState


StageClass: TypeAlias = type[Stage]


class StageRunner:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def initial_checkpoint(self, stage: Stage, status: str = "running") -> StageState:
        return build_initial_checkpoint(self.ctx, stage, status)

    def write_checkpoint(self, stage: Stage, checkpoint: StageState) -> None:
        paths = stage.artifact_paths()
        paths["stage_dir"].mkdir(parents=True, exist_ok=True)
        write_json_file(paths["checkpoint"], checkpoint)

    def write_metrics(self, stage: Stage, checkpoint: StageState) -> StageMetrics:
        paths = stage.artifact_paths()
        metrics = build_stage_metrics(checkpoint)
        write_json_file(paths["metrics"], metrics)
        return metrics

    def append_output(self, stage: Stage, item: StageItem) -> None:
        paths = stage.artifact_paths()
        paths["stage_dir"].mkdir(parents=True, exist_ok=True)
        append_jsonl_item(paths["output"], item)

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
        paths = stage.artifact_paths()
        return read_checkpoint_file(paths["checkpoint"])

    def run_stage(self, stage_cls: StageClass) -> StageState:
        stage = stage_cls(self.ctx)
        stage.ensure_stage_dir()
        update_stage_status(self.ctx, stage.name, "running")
        checkpoint = self.initial_checkpoint(stage)
        previous_checkpoint = self.read_checkpoint(stage)
        checkpoint = merge_previous_checkpoint(checkpoint, previous_checkpoint)
        inputs = list(stage.load_input())
        checkpoint["input_count"] = len(inputs)
        start_index = next_start_index(checkpoint)
        self.write_checkpoint(stage, checkpoint)
        start_time = start_timer()

        try:
            for index, item in enumerate(inputs[start_index:], start=start_index):
                output_item = stage.process_item(item)
                self.append_output(stage, output_item)
                record_processed_item(checkpoint, index, output_item)
                self.write_checkpoint(stage, checkpoint)
        except Exception as exc:
            failure_status = record_stage_failure(checkpoint, exc, start_time)
            self.write_checkpoint(stage, checkpoint)
            self.write_metrics(stage, checkpoint)
            update_stage_status(self.ctx, stage.name, failure_status)
            raise

        record_stage_completion(checkpoint, start_time)
        self.write_checkpoint(stage, checkpoint)
        self.write_metrics(stage, checkpoint)
        update_stage_status(self.ctx, stage.name, "completed")
        return checkpoint
