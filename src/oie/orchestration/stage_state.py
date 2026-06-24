from __future__ import annotations

from typing import TypedDict

from oie.orchestration.stage_costs import CostEstimate
from oie.orchestration.stage_errors import ErrorRecord
from oie.orchestration.stage_provider_usage import ProviderUsage


class StageState(TypedDict):
    run_id: str
    stage: str
    status: str
    input_count: int
    processed_count: int
    output_count: int
    rejected_count: int
    last_processed_index: int | None
    last_processed_id: str | None
    errors: list[ErrorRecord]
    provider_usage: ProviderUsage
    cost_estimate: CostEstimate
    processing_time_seconds: float
