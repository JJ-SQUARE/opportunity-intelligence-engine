from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from oie.api.schemas.runs import (
    ArtifactCatalogResponse,
    CreateRunRequest,
    CreateRunResponse,
    ErrorResponse,
    ExecuteRunRequest,
    HTTPErrorResponse,
    HubSpotDeliveryRequest,
    HubSpotDeliveryResponse,
    RunExecutionResponse,
    RunMetricsSummaryResponse,
    RunScheduleRequest,
    RunScheduleResponse,
    RunScheduleStatusResponse,
    StageCheckpointResponse,
    StageMetricsResponse,
    StageArtifactSummaryResponse,
    RunStageStatusResponse,
    RunStatusResponse,
    RunSummaryResponse,
)
from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.collect_jobs_stage import CollectJobsStage
from oie.orchestration.normalize_jobs_stage import NormalizeJobsStage
from oie.orchestration.company_gate_stage import CompanyGateStage
from oie.orchestration.job_intelligence_stage import JobIntelligenceStage
from oie.orchestration.pipeline_orchestrator import PipelineOrchestrator
from oie.orchestration.stage_runner import StageRunner
from oie.orchestration.pipeline_stages import PIPELINE_STAGES
from oie.orchestration.run_context import RunConfig, RunContext, RunFlags
from oie.orchestration.run_manifest import build_initial_manifest, finalize_manifest, write_manifest
from oie.orchestration.run_schedule import read_run_schedule, run_schedule_status, write_run_schedule
from oie.orchestration.run_repository import RunRepository
from oie.orchestration.stage_artifact_repository import StageArtifactRepository

router = APIRouter(tags=["Runs"], responses={404: {"model": HTTPErrorResponse}})


def _run_repository() -> RunRepository:
    return RunRepository.create()


def _stage_artifact_repository(
    run_id: str,
    stage_name: str,
    not_found_detail: str,
) -> StageArtifactRepository:
    repository = _run_repository()
    stage = repository.read_stage(run_id, stage_name)
    if stage is None:
        raise HTTPException(status_code=404, detail=not_found_detail)
    return StageArtifactRepository(repository.ctx, run_id)


def _ctx_for_existing_run(
    run_id: str,
    config: RunConfig,
    flags: RunFlags,
    mode: str | None,
) -> RunContext:
    repository_ctx = RunContext.create(config=config, flags=flags, mode=mode)
    repository = RunRepository(repository_ctx)
    manifest = repository.read_detail(run_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")

    ctx = RunContext.create(
        config=config,
        flags=flags,
        mode=mode or str(manifest.get("mode") or "default"),
    )
    ctx.run_id = run_id
    ctx.run_date = str(manifest.get("run_date") or ctx.run_date)
    ctx.mode = str(manifest.get("mode") or ctx.mode)

    runs_base_dir = ctx.paths["runs_base_dir"]
    run_dir = f"{runs_base_dir}/{run_id}"
    ctx.paths["run_dir"] = run_dir
    ctx.paths["manifest_path"] = f"{run_dir}/manifest.json"
    ctx.paths["stage_dirs"] = {
        stage: f"{run_dir}/{index:02d}_{stage}"
        for index, stage in enumerate(PIPELINE_STAGES, start=1)
    }
    return ctx


def _update_run_status(
    run_id: str,
    request: ExecuteRunRequest,
    status: str,
    current_stage: str | None = None,
) -> JSONPayload:
    ctx = _ctx_for_existing_run(
        run_id=run_id,
        config=request.config,
        flags=request.flags,
        mode=request.mode,
    )
    repository = RunRepository(ctx)
    manifest = repository.read_detail(run_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")

    manifest["status"] = status
    manifest["current_stage"] = current_stage
    write_manifest(ctx, manifest)

    updated_status = repository.read_status(run_id)
    if updated_status is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return updated_status


@router.post("/runs", summary="Create run", response_model=CreateRunResponse)
def create_run(request: CreateRunRequest) -> CreateRunResponse:
    ctx = RunContext.create(
        config=request.config,
        flags=request.flags,
        mode=request.mode,
    )
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)
    return CreateRunResponse(
        run_id=manifest["run_id"],
        status=manifest["status"],
        current_stage=manifest["current_stage"],
        manifest_path=ctx.paths["manifest_path"],
    )


@router.post("/runs/{run_id}/execute", summary="Execute run", response_model=RunExecutionResponse)
def execute_run(run_id: str, request: ExecuteRunRequest) -> JSONPayload:
    ctx = _ctx_for_existing_run(
        run_id=run_id,
        config=request.config,
        flags=request.flags,
        mode=request.mode,
    )
    if request.start_stage is not None:
        start_index = PIPELINE_STAGES.index(request.start_stage) if request.start_stage in PIPELINE_STAGES else -1
        if start_index < 0:
            raise HTTPException(status_code=404, detail="Stage not found")
        executable_stages = [
            stage_name
            for stage_name in PIPELINE_STAGES[start_index:]
            if stage_name in STAGE_CLASSES
        ]
        if not executable_stages:
            raise HTTPException(status_code=404, detail="Stage not executable")

        last_checkpoint = None
        runner = StageRunner(ctx)
        for executable_stage in executable_stages:
            last_checkpoint = runner.run_stage(STAGE_CLASSES[executable_stage])

        finalize_manifest(ctx, "completed")
        return {
            "run_id": ctx.run_id,
            "status": "completed",
            "jobs_count": int((last_checkpoint or {}).get("output_count", 0)),
            "companies_count": 0,
            "leads_count": 0,
        }

    result = PipelineOrchestrator(ctx).run()
    return dict(result)


STAGE_CLASSES = {
    "collect_jobs": CollectJobsStage,
    "company_gate": NormalizeJobsStage,
    "freshness_gate": JobIntelligenceStage,
    "domain_gate": CompanyGateStage,
}


@router.post("/runs/{run_id}/stages/{stage_name}/execute", summary="Execute run stage", response_model=StageCheckpointResponse)
def execute_run_stage(run_id: str, stage_name: str, request: ExecuteRunRequest) -> JSONPayload:
    stage_cls = STAGE_CLASSES.get(stage_name)
    if stage_cls is None:
        raise HTTPException(status_code=404, detail="Stage not executable")

    ctx = _ctx_for_existing_run(
        run_id=run_id,
        config=request.config,
        flags=request.flags,
        mode=request.mode,
    )
    checkpoint = StageRunner(ctx).run_stage(stage_cls)
    return dict(checkpoint)


@router.post("/runs/{run_id}/cancel", summary="Cancel run", response_model=RunStatusResponse)
def cancel_run(run_id: str, request: ExecuteRunRequest) -> JSONPayload:
    return _update_run_status(
        run_id=run_id,
        request=request,
        status="cancelled",
        current_stage=None,
    )


@router.post("/runs/{run_id}/pause", summary="Pause run", response_model=RunStatusResponse)
def pause_run(run_id: str, request: ExecuteRunRequest) -> JSONPayload:
    return _update_run_status(
        run_id=run_id,
        request=request,
        status="waiting_for_user",
    )


@router.post("/runs/{run_id}/resume", summary="Resume run", response_model=RunStatusResponse)
def resume_run(run_id: str, request: ExecuteRunRequest) -> JSONPayload:
    return _update_run_status(
        run_id=run_id,
        request=request,
        status="pending",
    )


@router.get("/runs", summary="List runs", response_model=list[RunSummaryResponse])
def list_runs(
    account_id: str | None = None,
    user_id: str | None = None,
) -> list[JSONPayload]:
    repository = _run_repository()
    return repository.list_summaries(account_id=account_id, user_id=user_id)


@router.get("/runs/{run_id}/status", summary="Get run status", response_model=RunStatusResponse)
def get_run_status(run_id: str) -> JSONPayload:
    repository = _run_repository()
    status = repository.read_status(run_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return status


@router.post("/runs/{run_id}/schedule", summary="Create run schedule", response_model=RunScheduleResponse)
def create_run_schedule(run_id: str, request: RunScheduleRequest) -> JSONPayload:
    return _write_schedule_response(run_id, request)


@router.put("/runs/{run_id}/schedule", summary="Update run schedule", response_model=RunScheduleResponse)
def update_run_schedule(run_id: str, request: RunScheduleRequest) -> JSONPayload:
    return _write_schedule_response(run_id, request)


def _write_schedule_response(run_id: str, request: RunScheduleRequest) -> JSONPayload:
    ctx = _ctx_for_existing_run(
        run_id=run_id,
        config={},
        flags={},
        mode=None,
    )
    try:
        return write_run_schedule(ctx, request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/runs/{run_id}/hubspot-delivery", summary="Update run HubSpot delivery", response_model=HubSpotDeliveryResponse)
def update_run_hubspot_delivery(run_id: str, request: HubSpotDeliveryRequest) -> JSONPayload:
    ctx = _ctx_for_existing_run(
        run_id=run_id,
        config={},
        flags={},
        mode=None,
    )
    repository = RunRepository(ctx)
    manifest = repository.read_detail(run_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")

    hubspot_delivery = {
        key: value
        for key, value in request.model_dump(exclude_none=True).items()
        if key != "hubspot_bearer_token"
    }
    if "hubspot_bearer_token" in request.model_fields_set and request.hubspot_bearer_token:
        account_id = str((manifest.get("account", {}) or {}).get("account_id") or "unknown-account")
        user_id = str((manifest.get("user", {}) or {}).get("user_id") or "unknown-user")
        hubspot_delivery["hubspot_credentials_ref"] = (
            hubspot_delivery.get("hubspot_credentials_ref")
            or f"hubspot/{account_id}/{user_id}"
        )

    manifest["hubspot_delivery"] = hubspot_delivery
    write_manifest(ctx, manifest)
    return {"run_id": run_id, "hubspot_delivery": hubspot_delivery}


@router.get("/runs/{run_id}/schedule/status", summary="Get run schedule status", response_model=RunScheduleStatusResponse)
def get_run_schedule_status(run_id: str) -> JSONPayload:
    ctx = _ctx_for_existing_run(
        run_id=run_id,
        config={},
        flags={},
        mode=None,
    )
    return run_schedule_status(ctx)


@router.get("/runs/{run_id}/schedule", summary="Get run schedule", response_model=RunScheduleResponse)
def get_run_schedule(run_id: str) -> JSONPayload:
    ctx = _ctx_for_existing_run(
        run_id=run_id,
        config={},
        flags={},
        mode=None,
    )
    schedule = read_run_schedule(ctx)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Run schedule not found")
    return schedule


@router.get("/runs/{run_id}/stages", summary="List run stages", response_model=list[RunStageStatusResponse])
def get_run_stages(run_id: str) -> list[JSONPayload]:
    repository = _run_repository()
    stages = repository.read_stages(run_id)
    if stages is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return stages


@router.get("/runs/{run_id}/artifacts", summary="Get artifact catalog", response_model=ArtifactCatalogResponse)
def get_run_artifact_catalog(run_id: str) -> JSONPayload:
    repository = _run_repository()
    manifest = repository.read_detail(run_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return StageArtifactRepository(repository.ctx, run_id).read_catalog()


@router.get("/runs/{run_id}/stages/{stage_name}", summary="Get stage status", response_model=RunStageStatusResponse)
def get_run_stage(run_id: str, stage_name: str) -> JSONPayload:
    repository = _run_repository()
    stage = repository.read_stage(run_id, stage_name)
    if stage is None:
        raise HTTPException(status_code=404, detail="Stage not found")
    return stage


@router.get("/runs/{run_id}/stages/{stage_name}/summary", summary="Get stage artifact summary", response_model=StageArtifactSummaryResponse)
def get_run_stage_artifact_summary(run_id: str, stage_name: str) -> JSONPayload:
    repository = _stage_artifact_repository(run_id, stage_name, "Stage artifact summary not found")
    return repository.read_summary(stage_name)


@router.get("/runs/{run_id}/stages/{stage_name}/checkpoint", summary="Get stage checkpoint", response_model=StageCheckpointResponse)
def get_run_stage_checkpoint(run_id: str, stage_name: str) -> JSONPayload:
    repository = _stage_artifact_repository(run_id, stage_name, "Checkpoint not found")
    checkpoint = repository.read_checkpoint(stage_name)
    if checkpoint is None:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return checkpoint


@router.get("/runs/{run_id}/stages/{stage_name}/metrics", summary="Get stage metrics", response_model=StageMetricsResponse)
def get_run_stage_metrics(run_id: str, stage_name: str) -> JSONPayload:
    repository = _stage_artifact_repository(run_id, stage_name, "Stage metrics not found")
    metrics = repository.read_metrics(stage_name)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Stage metrics not found")
    return metrics


@router.get("/runs/{run_id}/stages/{stage_name}/output", summary="Get stage output", response_model=list[dict[str, Any]])
def get_run_stage_output(run_id: str, stage_name: str) -> list[JSONPayload]:
    repository = _stage_artifact_repository(run_id, stage_name, "Stage output not found")
    output = repository.read_output(stage_name)
    if output is None:
        raise HTTPException(status_code=404, detail="Stage output not found")
    return output


@router.get("/runs/{run_id}/stages/{stage_name}/errors", summary="Get stage errors", response_model=list[ErrorResponse])
def get_run_stage_errors(run_id: str, stage_name: str) -> list[JSONPayload]:
    repository = _stage_artifact_repository(run_id, stage_name, "Stage errors not found")
    errors = repository.read_errors(stage_name)
    if errors is None:
        raise HTTPException(status_code=404, detail="Stage errors not found")
    return errors


@router.get("/runs/{run_id}/errors", summary="Get run errors", response_model=list[ErrorResponse])
def get_run_errors(run_id: str) -> list[JSONPayload]:
    repository = _run_repository()
    errors = repository.read_errors(run_id)
    if errors is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return errors


@router.get("/runs/{run_id}/metrics", summary="Get run metrics summary", response_model=RunMetricsSummaryResponse)
def get_run_metrics(run_id: str) -> JSONPayload:
    repository = _run_repository()
    metrics = repository.read_metrics_summary(run_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return metrics


@router.get("/runs/{run_id}", summary="Get run detail", response_model=dict[str, Any])
def get_run_detail(run_id: str) -> JSONPayload:
    repository = _run_repository()
    detail = repository.read_detail(run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return detail
