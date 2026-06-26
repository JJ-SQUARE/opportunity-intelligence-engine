from __future__ import annotations

from pathlib import Path
from typing import cast

from oie.orchestration.run_context import RunContext
from oie.orchestration.stage_io import read_json_file
from oie.orchestration.stage_state import StageState

from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_item import StageItem
from oie.orchestration.stage_errors import build_error_record
from oie.orchestration.stage_status import failure_status_for_checkpoint
from oie.orchestration.stage_timing import elapsed_seconds


def build_initial_checkpoint(ctx: RunContext, stage: Stage, status: str = "running") -> StageState:
    return {
        "run_id": ctx.run_id,
        "stage": stage.name,
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


REQUIRED_CHECKPOINT_FIELDS = {
    "run_id",
    "stage",
    "status",
    "input_count",
    "processed_count",
    "output_count",
    "rejected_count",
    "last_processed_index",
    "last_processed_id",
    "errors",
    "provider_usage",
    "cost_estimate",
    "processing_time_seconds",
}


def load_checkpoint_payload(checkpoint: object) -> StageState:
    if not isinstance(checkpoint, dict):
        raise TypeError("Checkpoint payload must be a JSON object.")

    missing_fields = REQUIRED_CHECKPOINT_FIELDS - set(checkpoint)
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(f"Checkpoint payload missing required fields: {missing}")

    return cast(StageState, checkpoint)


def read_checkpoint_file(path: Path) -> StageState | None:
    checkpoint = read_json_file(path)
    if checkpoint is None:
        return None
    return load_checkpoint_payload(checkpoint)


def merge_previous_checkpoint(checkpoint: StageState, previous_checkpoint: StageState | None) -> StageState:
    if previous_checkpoint:
        checkpoint.update(previous_checkpoint)
        checkpoint["status"] = "running"
        checkpoint["errors"] = []
    return checkpoint


def next_start_index(checkpoint: StageState) -> int:
    if checkpoint.get("last_processed_index") is None:
        return 0
    return int(checkpoint["last_processed_index"]) + 1


def record_processed_item(checkpoint: StageState, index: int, output_item: StageItem) -> None:
    checkpoint["processed_count"] += 1
    checkpoint["output_count"] += 1
    checkpoint["last_processed_index"] = index
    checkpoint["last_processed_id"] = output_item.get("id")


def record_stage_failure(checkpoint: StageState, exc: Exception, start_time: float) -> str:
    failure_status = failure_status_for_checkpoint(checkpoint)
    checkpoint["status"] = failure_status
    checkpoint["errors"].append(build_error_record(exc))
    checkpoint["processing_time_seconds"] = elapsed_seconds(start_time)
    return failure_status


def record_stage_completion(checkpoint: StageState, start_time: float) -> None:
    checkpoint["status"] = "completed"
    checkpoint["processing_time_seconds"] = elapsed_seconds(start_time)
