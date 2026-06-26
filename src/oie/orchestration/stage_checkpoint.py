from __future__ import annotations

from typing import get_type_hints, cast

from oie.orchestration.stage_state import StageState


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


