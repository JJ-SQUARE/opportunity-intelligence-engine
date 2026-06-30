from __future__ import annotations

from pathlib import Path
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
    RunConfigurationResponse,
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
from oie.orchestration.run_manifest import build_initial_manifest, finalize_manifest, set_run_status
from oie.orchestration.run_schedule import read_run_schedule, run_schedule_status, write_run_schedule
from oie.orchestration.run_repository import RunRepository
from oie.orchestration.stage_artifact_repository import StageArtifactRepository
from oie.orchestration.run_storage_resolver import configure_ctx_for_run_storage

router = APIRouter(tags=["Runs"], responses={404: {"model": HTTPErrorResponse}})


def _run_repository(
    run_id: str | None = None,
    config: RunConfig | None = None,
    flags: RunFlags | None = None,
    mode: str | None = None,
) -> RunRepository:
    ctx = RunContext.create(config=config, flags=flags, mode=mode)
    if run_id is not None:
        configure_ctx_for_run_storage(ctx, run_id)
    return RunRepository(ctx)



def _stage_artifact_repository(
    run_id: str,
    stage_name: str,
    not_found_detail: str,
) -> StageArtifactRepository:
    repository = _run_repository(run_id)
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
    repository = _run_repository(
        run_id=run_id,
        config={**config, "runs": config.get("runs", {})},
        flags=flags,
        mode=mode,
    )
    manifest = repository.read_detail(run_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")

    merged_config = dict(config)
    for metadata_key in ("account", "user", "hubspot_delivery"):
        if metadata_key not in merged_config and manifest.get(metadata_key):
            merged_config[metadata_key] = dict(manifest.get(metadata_key, {}) or {})

    ctx = RunContext.create(
        config=merged_config,
        flags=flags,
        mode=mode or str(manifest.get("mode") or "default"),
    )
    configure_ctx_for_run_storage(ctx, run_id)
    ctx.run_date = str(manifest.get("run_date") or ctx.run_date)
    ctx.mode = str(manifest.get("mode") or ctx.mode)
    return ctx


@router.post("/runs", summary="Create run", response_model=CreateRunResponse)
def create_run(request: CreateRunRequest) -> CreateRunResponse:
    ctx = RunContext.create(
        config=request.config,
        flags=request.flags,
        mode=request.mode,
    )
    manifest = build_initial_manifest(ctx)
    configuration_path = Path(ctx.paths["run_dir"]) / "configuration.json"
    manifest["config_path"] = str(configuration_path)
    repository = RunRepository(ctx)
    repository.write_detail(manifest)
    configuration_path = repository.write_configuration(
        configuration_path,
        repository.build_configuration(),
    )
    return CreateRunResponse(
        run_id=manifest["run_id"],
        status=manifest["status"],
        current_stage=manifest["current_stage"],
        manifest_path=ctx.paths["manifest_path"],
        configuration_path=str(configuration_path),
    )


@router.post("/runs/{run_id}/execute", summary="Execute run", response_model=RunExecutionResponse)
def execute_run(run_id: str, request: ExecuteRunRequest) -> JSONPayload:
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

        ctx = _ctx_for_existing_run(
            run_id=run_id,
            config=request.config,
            flags=request.flags,
            mode=request.mode,
        )
        last_checkpoint = None
        runner = StageRunner(ctx)
        for executable_stage in executable_stages:
            last_checkpoint = runner.run_stage(
                STAGE_CLASSES[executable_stage],
                reset=request.rerun,
            )

        finalize_manifest(ctx, "completed")
        return {
            "run_id": ctx.run_id,
            "status": "completed",
            "jobs_count": int((last_checkpoint or {}).get("output_count", 0)),
            "companies_count": 0,
            "leads_count": 0,
        }

    ctx = _ctx_for_existing_run(
        run_id=run_id,
        config=request.config,
        flags=request.flags,
        mode=request.mode,
    )
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
    checkpoint = StageRunner(ctx).run_stage(stage_cls, reset=request.rerun)
    return dict(checkpoint)



@router.post("/runs/{run_id}/cancel", response_model=RunStatusResponse)
def cancel_run(run_id: str, request: ExecuteRunRequest) -> JSONPayload:
    ctx = _ctx_for_existing_run(run_id, request.config, request.flags, request.mode)
    return set_run_status(ctx, run_id, "cancelled")




@router.post("/runs/{run_id}/pause", response_model=RunStatusResponse)
def pause_run(run_id: str, request: ExecuteRunRequest) -> JSONPayload:
    ctx = _ctx_for_existing_run(run_id, request.config, request.flags, request.mode)
    return set_run_status(ctx, run_id, "waiting_for_user")




@router.post("/runs/{run_id}/resume", response_model=RunStatusResponse)
def resume_run(run_id: str, request: ExecuteRunRequest) -> JSONPayload:
    ctx = _ctx_for_existing_run(run_id, request.config, request.flags, request.mode)
    return set_run_status(ctx, run_id, "pending")



@router.get("/runs", summary="List runs", response_model=list[RunSummaryResponse])
def list_runs(
    account_id: str | None = None,
    user_id: str | None = None,
) -> list[JSONPayload]:
    repository = _run_repository()
    return repository.list_summaries(account_id=account_id, user_id=user_id)


@router.get("/runs/{run_id}/status", summary="Get run status", response_model=RunStatusResponse)
def get_run_status(run_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    status = repository.read_status(run_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return status


@router.get("/runs/{run_id}/configuration", summary="Get run configuration", response_model=RunConfigurationResponse)
def get_run_configuration(run_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    if repository.read_detail(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")

    configuration = repository.read_configuration(run_id)
    if configuration is None:
        raise HTTPException(status_code=404, detail="Run configuration not found")
    return configuration


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
    repository = _run_repository(run_id)
    manifest = repository.read_detail(run_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")

    account = manifest.get("account", {}) or {}
    user = manifest.get("user", {}) or {}

    hubspot_delivery = {
        key: value
        for key, value in request.model_dump(exclude_none=True).items()
        if key != "hubspot_bearer_token"
    }
    if "hubspot_bearer_token" in request.model_fields_set and request.hubspot_bearer_token:
        account_id = str(account.get("account_id") or "unknown-account")
        user_id = str(user.get("user_id") or "unknown-user")
        hubspot_delivery["hubspot_credentials_ref"] = (
            hubspot_delivery.get("hubspot_credentials_ref")
            or f"hubspot/{account_id}/{user_id}"
        )

    manifest["hubspot_delivery"] = hubspot_delivery
    repository.write_detail(manifest)

    persisted = repository.read_detail(run_id)
    if persisted is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return {
        "run_id": run_id,
        "hubspot_delivery": persisted.get("hubspot_delivery", {}),
    }


@router.get(
    "/runs/{run_id}/hubspot-delivery",
    summary="Get run HubSpot delivery",
    response_model=HubSpotDeliveryResponse,
)
def get_run_hubspot_delivery(run_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    detail = repository.read_detail(run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return {
        "run_id": run_id,
        "hubspot_delivery": detail.get("hubspot_delivery", {}),
    }


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
    repository = _run_repository(run_id)
    stages = repository.read_stages(run_id)
    if stages is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return stages


@router.get("/runs/{run_id}/artifacts", summary="Get artifact catalog", response_model=ArtifactCatalogResponse)
def get_run_artifact_catalog(run_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    manifest = repository.read_detail(run_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return StageArtifactRepository(repository.ctx, run_id).read_catalog()


@router.get("/runs/{run_id}/stages/{stage_name}", summary="Get stage status", response_model=RunStageStatusResponse)
def get_run_stage(run_id: str, stage_name: str) -> JSONPayload:
    repository = _run_repository(run_id)
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
    repository = _run_repository(run_id)
    errors = repository.read_errors(run_id)
    if errors is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return errors


@router.get("/runs/{run_id}/metrics", summary="Get run metrics summary", response_model=RunMetricsSummaryResponse)
def get_run_metrics(run_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    metrics = repository.read_metrics_summary(run_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return metrics


@router.get("/runs/{run_id}", summary="Get run detail", response_model=dict[str, Any])
def get_run_detail(run_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    detail = repository.read_detail(run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return detail
