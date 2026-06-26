from __future__ import annotations

from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint import merge_previous_checkpoint, next_start_index, read_checkpoint_file, record_processed_item, record_stage_completion, record_stage_failure
from oie.orchestration.stage_io import append_jsonl_item, write_json_file
from oie.orchestration.stage_item import StageItem
from oie.orchestration.stage_metrics import StageMetrics, build_stage_metrics
from oie.orchestration.stage_state import StageState


class StageCheckpointManager:
    def __init__(self, stage: Stage) -> None:
        self.stage = stage

    def initial_checkpoint(self, status: str = "running") -> StageState:
        return {
            "run_id": self.stage.ctx.run_id,
            "stage": self.stage.name,
            "status": status,
            "input_count": 0,
            "processed_count": 0,
            "output_count": 0,
            "rejected_count": 0,
            "last_processed_index": None,
            "last_processed_id": None,
            "errors": [],
            "provider_usage": {},
            "cost_estimate": {},
            "processing_time_seconds": 0.0,
        }

    def read_checkpoint(self) -> StageState | None:
        paths = self.stage.artifact_paths()
        return read_checkpoint_file(paths["checkpoint"])

    def merge_previous_checkpoint(
        self,
        checkpoint: StageState,
        previous_checkpoint: StageState | None,
    ) -> StageState:
        return merge_previous_checkpoint(checkpoint, previous_checkpoint)

    def next_start_index(self, checkpoint: StageState) -> int:
        return next_start_index(checkpoint)

    def prepare_checkpoint(self, input_count: int) -> tuple[StageState, int]:
        checkpoint = self.initial_checkpoint()
        previous_checkpoint = self.read_checkpoint()
        checkpoint = self.merge_previous_checkpoint(checkpoint, previous_checkpoint)
        checkpoint["input_count"] = input_count
        start_index = self.next_start_index(checkpoint)
        self.write_checkpoint(checkpoint)
        return checkpoint, start_index

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

    def record_processed_item(self, checkpoint: StageState, index: int, output_item: StageItem) -> None:
        record_processed_item(checkpoint, index, output_item)

    def record_stage_completion(self, checkpoint: StageState, start_time: float) -> None:
        record_stage_completion(checkpoint, start_time)

    def record_stage_failure(self, checkpoint: StageState, exc: Exception, start_time: float) -> str:
        return record_stage_failure(checkpoint, exc, start_time)
