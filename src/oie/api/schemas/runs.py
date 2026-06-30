from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from oie.orchestration.run_context import RunConfig, RunFlags


class CreateRunRequest(BaseModel):
    config: RunConfig = Field(default_factory=dict)
    flags: RunFlags = Field(default_factory=dict)
    mode: str | None = None


class CreateRunResponse(BaseModel):
    run_id: str
    status: str
    current_stage: str | None
    manifest_path: str


class ExecuteRunRequest(BaseModel):
    config: RunConfig = Field(default_factory=dict)
    flags: RunFlags = Field(default_factory=dict)
    mode: str | None = None


class RunSummaryResponse(BaseModel):
    run_id: str
    status: str
    current_stage: str | None
    created_at: str
    updated_at: str


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    current_stage: str | None


class RunExecutionResponse(BaseModel):
    run_id: str
    status: str
    jobs_count: int
    companies_count: int
    leads_count: int


class RunStageStatusResponse(BaseModel):
    stage: str
    status: str


class RunMetricsSummaryResponse(BaseModel):
    run_id: str
    stage_count: int
    error_count: int
    status_counts: dict[str, int]


class ErrorResponse(BaseModel):
    error_type: str
    error_message: str


class StageCheckpointResponse(BaseModel):
    run_id: str
    stage: str
    status: str
    input_count: int
    processed_count: int
    output_count: int
    rejected_count: int
    last_processed_index: int | None
    last_processed_id: str | None
    errors: list[ErrorResponse]
    provider_usage: dict[str, Any]
    cost_estimate: dict[str, Any]
    processing_time_seconds: float


class StageMetricsResponse(BaseModel):
    run_id: str
    stage: str
    status: str
    input_count: int
    processed_count: int
    output_count: int
    rejected_count: int
    error_count: int
    provider_usage: dict[str, Any]
    cost_estimate: dict[str, Any]
    processing_time_seconds: float
