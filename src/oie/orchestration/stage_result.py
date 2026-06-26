from __future__ import annotations

from typing import TypedDict

from oie.orchestration.stage_metrics import StageMetrics
from oie.orchestration.stage_state import StageState


class StageResult(TypedDict):
    run_id: str
    stage: str
    status: str
    checkpoint: StageState
    metrics: StageMetrics


def build_stage_result(checkpoint: StageState, metrics: StageMetrics) -> StageResult:
    return {
        "run_id": checkpoint["run_id"],
        "stage": checkpoint["stage"],
        "status": checkpoint["status"],
        "checkpoint": checkpoint,
        "metrics": metrics,
    }
