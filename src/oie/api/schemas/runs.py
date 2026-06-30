from __future__ import annotations

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


class RunStageStatusResponse(BaseModel):
    stage: str
    status: str


class RunMetricsSummaryResponse(BaseModel):
    run_id: str
    stage_count: int
    error_count: int
    status_counts: dict[str, int]
