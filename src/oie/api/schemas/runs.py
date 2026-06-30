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
    configuration_path: str


class ExecuteRunRequest(BaseModel):
    config: RunConfig = Field(default_factory=dict)
    flags: RunFlags = Field(default_factory=dict)
    mode: str | None = None
    start_stage: str | None = None
    rerun: bool = False


class RunSummaryResponse(BaseModel):
    run_id: str
    status: str
    current_stage: str | None
    created_at: str
    updated_at: str
    account: dict[str, Any] = Field(default_factory=dict)
    user: dict[str, Any] = Field(default_factory=dict)
    hubspot_delivery: dict[str, Any] = Field(default_factory=dict)


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    current_stage: str | None


class RunConfigurationResponse(BaseModel):
    runs: dict[str, Any] = Field(default_factory=dict)
    account: dict[str, Any] = Field(default_factory=dict)
    user: dict[str, Any] = Field(default_factory=dict)
    hubspot_delivery: dict[str, Any] = Field(default_factory=dict)
    icp_profiles: list[dict[str, Any]] = Field(default_factory=list)
    flags: dict[str, Any] = Field(default_factory=dict)
    mode: str


class RunScheduleRequest(BaseModel):
    frequency: str
    duration: str
    scheduled_times: list[str] = Field(default_factory=list)
    scheduled_days: list[str] = Field(default_factory=list)
    enabled: bool = True


class RunScheduleResponse(BaseModel):
    run_id: str
    frequency: str
    duration: str
    scheduled_times: list[str]
    scheduled_days: list[str]
    enabled: bool


class RunScheduleStatusResponse(BaseModel):
    run_id: str
    scheduled: bool
    enabled: bool
    due: bool
    frequency: str | None = None
    duration: str | None = None
    scheduled_times: list[str] = Field(default_factory=list)
    scheduled_days: list[str] = Field(default_factory=list)
    checked_at: str | None = None


class HubSpotDeliveryRequest(BaseModel):
    hubspot_user_id: str | None = None
    hubspot_owner_id: str | None = None
    hubspot_company_id: str | None = None
    hubspot_credentials_ref: str | None = None
    hubspot_bearer_token: str | None = None


class HubSpotDeliveryResponse(BaseModel):
    run_id: str
    hubspot_delivery: dict[str, Any]


class ICPProfilesRequest(BaseModel):
    icp_profiles: list[dict[str, Any]] = Field(default_factory=list)


class ICPProfilesResponse(BaseModel):
    run_id: str
    icp_profiles: list[dict[str, Any]]


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


class HTTPErrorResponse(BaseModel):
    detail: str


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


class StageArtifactSummaryResponse(BaseModel):
    run_id: str
    stage: str
    has_checkpoint: bool
    has_metrics: bool
    has_output: bool
    status: str | None
    input_count: int
    processed_count: int
    output_count: int
    error_count: int
    artifact_paths: dict[str, str]


class ArtifactCatalogResponse(BaseModel):
    run_id: str
    artifacts: list[StageArtifactSummaryResponse]
