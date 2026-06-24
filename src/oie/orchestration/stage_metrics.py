from __future__ import annotations

from typing import TypedDict

from oie.orchestration.stage_costs import CostEstimate
from oie.orchestration.stage_provider_usage import ProviderUsage
from oie.orchestration.stage_state import StageState


class StageMetrics(TypedDict):
    run_id: str
    stage: str
    status: str
    input_count: int
    processed_count: int
    output_count: int
    rejected_count: int
    error_count: int
    provider_usage: ProviderUsage
    cost_estimate: CostEstimate
    processing_time_seconds: float


def build_stage_metrics(checkpoint: StageState) -> StageMetrics:
    return {
        "run_id": checkpoint["run_id"],
        "stage": checkpoint["stage"],
        "status": checkpoint["status"],
        "input_count": checkpoint["input_count"],
        "processed_count": checkpoint["processed_count"],
        "output_count": checkpoint["output_count"],
        "rejected_count": checkpoint["rejected_count"],
        "error_count": len(checkpoint["errors"]),
        "provider_usage": checkpoint["provider_usage"],
        "cost_estimate": checkpoint["cost_estimate"],
        "processing_time_seconds": checkpoint["processing_time_seconds"],
    }
