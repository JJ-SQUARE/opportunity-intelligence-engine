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
