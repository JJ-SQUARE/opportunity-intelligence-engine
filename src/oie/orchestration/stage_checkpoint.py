from __future__ import annotations

from pathlib import Path
from typing import get_type_hints, cast

from oie.orchestration.stage_io import read_json_file
from oie.orchestration.stage_state import StageState

from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_item import StageItem
from oie.orchestration.stage_errors import build_error_record
from oie.orchestration.stage_status import failure_status_for_checkpoint
from oie.orchestration.stage_timing import elapsed_seconds


REQUIRED_CHECKPOINT_FIELDS = set(get_type_hints(StageState))


CHECKPOINT_FIELD_TYPES = {
    "run_id": str,
    "stage": str,
    "status": str,
    "input_count": int,
    "processed_count": int,
    "output_count": int,
    "rejected_count": int,
    "last_processed_index": (int, type(None)),
    "last_processed_id": (str, type(None)),
    "errors": list,
    "provider_usage": dict,
    "cost_estimate": dict,
    "processing_time_seconds": (int, float),
}


def load_checkpoint_payload(checkpoint: object) -> StageState:
    if not isinstance(checkpoint, dict):
        raise TypeError("Checkpoint payload must be a JSON object.")

    missing_fields = REQUIRED_CHECKPOINT_FIELDS - set(checkpoint)
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(f"Checkpoint payload missing required fields: {missing}")

    for field_name, expected_type in CHECKPOINT_FIELD_TYPES.items():
        if not isinstance(checkpoint[field_name], expected_type):
            raise TypeError(f"Checkpoint field has invalid type: {field_name}")

    return cast(StageState, checkpoint)


def read_checkpoint_file(path: Path) -> StageState | None:
    checkpoint = read_json_file(path)
    if checkpoint is None:
        return None
    return load_checkpoint_payload(checkpoint)


def record_stage_failure(checkpoint: StageState, exc: Exception, start_time: float) -> str:
    failure_status = failure_status_for_checkpoint(checkpoint)
    checkpoint["status"] = failure_status
    checkpoint["errors"].append(build_error_record(exc))
    checkpoint["processing_time_seconds"] = elapsed_seconds(start_time)
    return failure_status


def record_stage_completion(checkpoint: StageState, start_time: float) -> None:
    checkpoint["status"] = "completed"
    checkpoint["processing_time_seconds"] = elapsed_seconds(start_time)
