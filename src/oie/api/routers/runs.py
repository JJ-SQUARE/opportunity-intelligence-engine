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
    ICPProfileRequest,
    ICPProfilesRequest,
    ICPProfilesResponse,
    RunExecutionResponse,
    RunConfigurationResponse,
    RunDeleteResponse,
    RunArtifactPathsResponse,
    RunOutputResponse,
    RunOutputsResponse,
    RunReadinessResponse,
    RunAnalyticsResponse,
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
from oie.orchestration.run_schedule import delete_run_schedule, read_run_schedule, run_schedule_status, write_run_schedule
from oie.orchestration.run_repository import RunRepository
from oie.orchestration.stage_artifact_repository import StageArtifactRepository
from oie.orchestration.run_storage_resolver import configure_ctx_for_run_storage

router = APIRouter(responses={404: {"model": HTTPErrorResponse}})


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

    if "icp_profiles" not in merged_config and manifest.get("icp_profiles"):
        merged_config["icp_profiles"] = list(manifest.get("icp_profiles", []) or [])

    ctx = RunContext.create(
        config=merged_config,
        flags=flags,
        mode=mode or str(manifest.get("mode") or "default"),
    )
    configure_ctx_for_run_storage(ctx, run_id)
    ctx.run_date = str(manifest.get("run_date") or ctx.run_date)
    ctx.mode = str(manifest.get("mode") or ctx.mode)
    return ctx


@router.post("/runs", summary="Create run", response_model=CreateRunResponse, tags=["Run Management"])
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


def executable_stages_from(start_stage: str) -> list[str]:
    start_index = PIPELINE_STAGES.index(start_stage) if start_stage in PIPELINE_STAGES else -1
    if start_index < 0:
        raise HTTPException(status_code=404, detail="Stage not found")

    executable_stages = [
        stage_name
        for stage_name in PIPELINE_STAGES[start_index:]
        if stage_name in STAGE_CLASSES
    ]
    if not executable_stages:
        raise HTTPException(status_code=404, detail="Stage not executable")
    return executable_stages


@router.post("/runs/{run_id}/execute", summary="Execute run", response_model=RunExecutionResponse, tags=["Run Management"])
def execute_run(run_id: str, request: ExecuteRunRequest) -> JSONPayload:
    if request.start_stage is not None:
        executable_stages = executable_stages_from(request.start_stage)

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


@router.post("/runs/{run_id}/stages/{stage_name}/execute", summary="Execute run stage", response_model=StageCheckpointResponse, tags=["Run Management"])
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



@router.post("/runs/{run_id}/cancel", response_model=RunStatusResponse, tags=["Run Management"])
def cancel_run(run_id: str, request: ExecuteRunRequest) -> JSONPayload:
    ctx = _ctx_for_existing_run(run_id, request.config, request.flags, request.mode)
    return set_run_status(ctx, run_id, "cancelled")




@router.post("/runs/{run_id}/pause", response_model=RunStatusResponse, tags=["Run Management"])
def pause_run(run_id: str, request: ExecuteRunRequest) -> JSONPayload:
    ctx = _ctx_for_existing_run(run_id, request.config, request.flags, request.mode)
    return set_run_status(ctx, run_id, "waiting_for_user")




@router.post("/runs/{run_id}/resume", response_model=RunStatusResponse, tags=["Run Management"])
def resume_run(run_id: str, request: ExecuteRunRequest) -> JSONPayload:
    ctx = _ctx_for_existing_run(run_id, request.config, request.flags, request.mode)
    return set_run_status(ctx, run_id, "pending")



@router.get("/runs", summary="List runs", response_model=list[RunSummaryResponse], tags=["Run Management"])
def list_runs(
    account_id: str | None = None,
    user_id: str | None = None,
) -> list[JSONPayload]:
    repository = _run_repository()
    return repository.list_summaries(account_id=account_id, user_id=user_id)


@router.delete("/runs/{run_id}", summary="Delete run", response_model=RunDeleteResponse, tags=["Run Management"])
def delete_run(run_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    deleted = repository.delete_run(run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run_id": run_id, "deleted": True}


@router.get("/runs/{run_id}/status", summary="Get run status", response_model=RunStatusResponse, tags=["Run Management"])
def get_run_status(run_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    status = repository.read_status(run_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return status


@router.get("/runs/{run_id}/configuration", summary="Get run configuration", response_model=RunConfigurationResponse, tags=["Run Management"])
def get_run_configuration(run_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    if repository.read_detail(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")

    configuration = repository.read_configuration(run_id)
    if configuration is None:
        raise HTTPException(status_code=404, detail="Run configuration not found")
    return configuration


@router.put("/runs/{run_id}/configuration", summary="Update run configuration", response_model=RunConfigurationResponse, tags=["Run Management"])
def update_run_configuration(run_id: str, request: CreateRunRequest) -> JSONPayload:
    repository = _run_repository(run_id)
    manifest = repository.read_detail(run_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")

    configuration_path_value = manifest.get("config_path")
    if not configuration_path_value:
        configuration_path_value = str(Path(repository.ctx.paths["run_dir"]) / "configuration.json")
        manifest["config_path"] = configuration_path_value

    updated_ctx = RunContext.create(
        config=request.config,
        flags=request.flags,
        mode=request.mode,
    )
    updated_repository = RunRepository(updated_ctx)
    configuration = updated_repository.build_configuration()

    safe_hubspot_delivery = {
        key: value
        for key, value in dict(configuration.get("hubspot_delivery", {}) or {}).items()
        if key != "hubspot_bearer_token"
    }
    configuration["hubspot_delivery"] = safe_hubspot_delivery

    repository.write_configuration(Path(configuration_path_value), configuration)

    manifest["account"] = dict(configuration.get("account", {}) or {})
    manifest["user"] = dict(configuration.get("user", {}) or {})
    manifest["hubspot_delivery"] = safe_hubspot_delivery
    manifest["icp_profiles"] = list(configuration.get("icp_profiles", []) or [])
    manifest["mode"] = str(configuration.get("mode") or manifest.get("mode") or "default")
    repository.write_detail(manifest)

    return configuration


@router.post("/runs/{run_id}/schedule", summary="Create run schedule", response_model=RunScheduleResponse, tags=["Run Scheduling"])
def create_run_schedule(run_id: str, request: RunScheduleRequest) -> JSONPayload:
    return _write_schedule_response(run_id, request)


@router.put("/runs/{run_id}/schedule", summary="Update run schedule", response_model=RunScheduleResponse, tags=["Run Scheduling"])
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


@router.put("/runs/{run_id}/hubspot-delivery", summary="Update run HubSpot delivery", response_model=HubSpotDeliveryResponse, tags=["CRM Delivery"])
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


@router.delete("/runs/{run_id}/hubspot-delivery", summary="Delete run HubSpot delivery", response_model=HubSpotDeliveryResponse, tags=["CRM Delivery"])
def delete_run_hubspot_delivery(run_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    manifest = repository.read_detail(run_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")

    manifest["hubspot_delivery"] = {}
    repository.write_detail(manifest)

    return {
        "run_id": run_id,
        "hubspot_delivery": {},
    }


@router.get(
    "/runs/{run_id}/hubspot-delivery",
    summary="Get run HubSpot delivery",
    response_model=HubSpotDeliveryResponse,
    tags=["CRM Delivery"],
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


@router.put("/runs/{run_id}/icp-profiles", summary="Update run ICP profiles", response_model=ICPProfilesResponse, tags=["ICP Configuration"])
def update_run_icp_profiles(run_id: str, request: ICPProfilesRequest) -> JSONPayload:
    repository = _run_repository(run_id)
    manifest = repository.read_detail(run_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")

    manifest["icp_profiles"] = request.icp_profiles
    repository.write_detail(manifest)

    return {
        "run_id": run_id,
        "icp_profiles": request.icp_profiles,
    }


@router.post("/runs/{run_id}/icp-profiles", summary="Add run ICP profile", response_model=ICPProfilesResponse, tags=["ICP Configuration"])
def add_run_icp_profile(run_id: str, request: ICPProfileRequest) -> JSONPayload:
    repository = _run_repository(run_id)
    manifest = repository.read_detail(run_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")

    profile_id = request.profile.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=422, detail="ICP profile requires profile_id")

    icp_profiles = list(manifest.get("icp_profiles", []) or [])
    if any(profile.get("profile_id") == profile_id for profile in icp_profiles):
        raise HTTPException(status_code=409, detail=f"ICP profile already exists: {profile_id}")

    icp_profiles.append(request.profile)
    manifest["icp_profiles"] = icp_profiles
    repository.write_detail(manifest)

    return {
        "run_id": run_id,
        "icp_profiles": icp_profiles,
    }


@router.get("/runs/{run_id}/icp-profiles", summary="Get run ICP profiles", response_model=ICPProfilesResponse, tags=["ICP Configuration"])
def get_run_icp_profiles(run_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    detail = repository.read_detail(run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return {
        "run_id": run_id,
        "icp_profiles": list(detail.get("icp_profiles", []) or []),
    }


@router.delete("/runs/{run_id}/icp-profiles/{profile_id}", summary="Delete run ICP profile", response_model=ICPProfilesResponse, tags=["ICP Configuration"])
def delete_run_icp_profile(run_id: str, profile_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    manifest = repository.read_detail(run_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")

    icp_profiles = list(manifest.get("icp_profiles", []) or [])
    remaining_profiles = [
        profile
        for profile in icp_profiles
        if profile.get("profile_id") != profile_id
    ]

    if len(remaining_profiles) == len(icp_profiles):
        raise HTTPException(status_code=404, detail=f"ICP profile not found: {profile_id}")

    manifest["icp_profiles"] = remaining_profiles
    repository.write_detail(manifest)

    return {
        "run_id": run_id,
        "icp_profiles": remaining_profiles,
    }


@router.delete("/runs/{run_id}/schedule", summary="Delete run schedule", tags=["Run Scheduling"])
def delete_run_schedule_endpoint(run_id: str) -> JSONPayload:
    ctx = _ctx_for_existing_run(
        run_id=run_id,
        config={},
        flags={},
        mode=None,
    )
    try:
        return delete_run_schedule(ctx)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}/schedule/status", summary="Get run schedule status", response_model=RunScheduleStatusResponse, tags=["Run Scheduling"])
def get_run_schedule_status(run_id: str) -> JSONPayload:
    ctx = _ctx_for_existing_run(
        run_id=run_id,
        config={},
        flags={},
        mode=None,
    )
    return run_schedule_status(ctx)


@router.get("/runs/{run_id}/schedule", summary="Get run schedule", response_model=RunScheduleResponse, tags=["Run Scheduling"])
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


@router.get("/runs/{run_id}/stages", summary="List run stages", response_model=list[RunStageStatusResponse], tags=["Run Artifacts"])
def get_run_stages(run_id: str) -> list[JSONPayload]:
    repository = _run_repository(run_id)
    stages = repository.read_stages(run_id)
    if stages is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return stages


@router.get("/runs/{run_id}/artifacts", summary="Get artifact catalog", response_model=ArtifactCatalogResponse, tags=["Run Artifacts"])
def get_run_artifact_catalog(run_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    manifest = repository.read_detail(run_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return StageArtifactRepository(repository.ctx, run_id).read_catalog()


@router.get("/runs/{run_id}/artifact-paths", summary="Get run artifact paths", response_model=RunArtifactPathsResponse, tags=["Run Artifacts"])
def get_run_artifact_paths(run_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    manifest = repository.read_detail(run_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return {
        "run_id": run_id,
        "artifact_paths": dict(manifest.get("artifact_paths", {}) or {}),
    }


def _artifact_format(path: str) -> str | None:
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix == ".jsonl":
        return "jsonl"
    if suffix == ".csv":
        return "csv"
    if suffix in {".md", ".txt"}:
        return "text"
    return None


def _safe_output_paths(manifest: JSONPayload) -> dict[str, str]:
    artifact_paths = dict(manifest.get("artifact_paths", {}) or {})
    return {
        str(name): str(path)
        for name, path in artifact_paths.items()
        if path
    }


def _read_output_content(path: Path, output_format: str) -> Any:
    if output_format == "json":
        from oie.orchestration.stage_io import read_json_file
        return read_json_file(path)
    if output_format == "jsonl":
        from oie.orchestration.stage_io import read_jsonl_file
        return read_jsonl_file(path)
    if output_format in {"csv", "text"}:
        return path.read_text(encoding="utf-8")
    raise HTTPException(status_code=415, detail=f"Unsupported artifact format: {path.suffix}")


@router.get("/runs/{run_id}/outputs", summary="List run outputs", response_model=RunOutputsResponse, tags=["Run Artifacts"])
def get_run_outputs(run_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    manifest = repository.read_detail(run_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")

    outputs = []
    for name, path_value in sorted(_safe_output_paths(manifest).items()):
        path = Path(path_value)
        outputs.append(
            {
                "name": name,
                "path": path_value,
                "exists": path.exists(),
                "format": _artifact_format(path_value),
            }
        )

    return {
        "run_id": run_id,
        "outputs": outputs,
    }


@router.get("/runs/{run_id}/outputs/{output_name}", summary="Get run output", response_model=RunOutputResponse, tags=["Run Artifacts"])
def get_run_output(run_id: str, output_name: str) -> JSONPayload:
    repository = _run_repository(run_id)
    manifest = repository.read_detail(run_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")

    outputs = _safe_output_paths(manifest)
    if output_name not in outputs:
        raise HTTPException(status_code=404, detail=f"Run output not found: {output_name}")

    path = Path(outputs[output_name])
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Run output file not found: {output_name}")

    output_format = _artifact_format(str(path))
    if output_format is None:
        raise HTTPException(status_code=415, detail=f"Unsupported artifact format: {path.suffix}")

    return {
        "run_id": run_id,
        "name": output_name,
        "path": str(path),
        "format": output_format,
        "content": _read_output_content(path, output_format),
    }


@router.get("/runs/{run_id}/readiness", summary="Get run readiness", response_model=RunReadinessResponse, tags=["Run Artifacts"])
def get_run_readiness(run_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    manifest = repository.read_detail(run_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")

    artifact_paths = dict(manifest.get("artifact_paths", {}) or {})
    readiness_path_value = artifact_paths.get("run_readiness_report_json")
    if not readiness_path_value:
        raise HTTPException(status_code=404, detail="Run readiness report not found")

    readiness_path = Path(str(readiness_path_value))
    if not readiness_path.exists():
        raise HTTPException(status_code=404, detail="Run readiness report file not found")

    from oie.orchestration.stage_io import read_json_file

    readiness = read_json_file(readiness_path)
    if readiness is None:
        raise HTTPException(status_code=404, detail="Run readiness report file not found")

    return {
        "run_id": run_id,
        "path": str(readiness_path),
        "readiness": readiness,
    }


@router.get("/runs/{run_id}/analytics", summary="Get run analytics", response_model=RunAnalyticsResponse, tags=["Run Artifacts"])
def get_run_analytics(run_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    manifest = repository.read_detail(run_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")

    artifact_paths = dict(manifest.get("artifact_paths", {}) or {})
    analytics_path_value = artifact_paths.get("run_analytics_json")
    if not analytics_path_value:
        raise HTTPException(status_code=404, detail="Run analytics not found")

    analytics_path = Path(str(analytics_path_value))
    if not analytics_path.exists():
        raise HTTPException(status_code=404, detail="Run analytics file not found")

    from oie.orchestration.stage_io import read_json_file

    analytics = read_json_file(analytics_path)
    if analytics is None:
        raise HTTPException(status_code=404, detail="Run analytics file not found")

    return {
        "run_id": run_id,
        "path": str(analytics_path),
        "analytics": analytics,
    }


@router.get("/runs/{run_id}/stages/{stage_name}", summary="Get stage status", response_model=RunStageStatusResponse, tags=["Run Artifacts"])
def get_run_stage(run_id: str, stage_name: str) -> JSONPayload:
    repository = _run_repository(run_id)
    stage = repository.read_stage(run_id, stage_name)
    if stage is None:
        raise HTTPException(status_code=404, detail="Stage not found")
    return stage


@router.get("/runs/{run_id}/stages/{stage_name}/summary", summary="Get stage artifact summary", response_model=StageArtifactSummaryResponse, tags=["Run Artifacts"])
def get_run_stage_artifact_summary(run_id: str, stage_name: str) -> JSONPayload:
    repository = _stage_artifact_repository(run_id, stage_name, "Stage artifact summary not found")
    return repository.read_summary(stage_name)


@router.get("/runs/{run_id}/stages/{stage_name}/checkpoint", summary="Get stage checkpoint", response_model=StageCheckpointResponse, tags=["Run Artifacts"])
def get_run_stage_checkpoint(run_id: str, stage_name: str) -> JSONPayload:
    repository = _stage_artifact_repository(run_id, stage_name, "Checkpoint not found")
    checkpoint = repository.read_checkpoint(stage_name)
    if checkpoint is None:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return checkpoint


@router.get("/runs/{run_id}/stages/{stage_name}/metrics", summary="Get stage metrics", response_model=StageMetricsResponse, tags=["Run Artifacts"])
def get_run_stage_metrics(run_id: str, stage_name: str) -> JSONPayload:
    repository = _stage_artifact_repository(run_id, stage_name, "Stage metrics not found")
    metrics = repository.read_metrics(stage_name)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Stage metrics not found")
    return metrics


@router.get("/runs/{run_id}/stages/{stage_name}/output", summary="Get stage output", response_model=list[dict[str, Any]], tags=["Run Artifacts"])
def get_run_stage_output(run_id: str, stage_name: str) -> list[JSONPayload]:
    repository = _stage_artifact_repository(run_id, stage_name, "Stage output not found")
    output = repository.read_output(stage_name)
    if output is None:
        raise HTTPException(status_code=404, detail="Stage output not found")
    return output


@router.get("/runs/{run_id}/stages/{stage_name}/errors", summary="Get stage errors", response_model=list[ErrorResponse], tags=["Run Artifacts"])
def get_run_stage_errors(run_id: str, stage_name: str) -> list[JSONPayload]:
    repository = _stage_artifact_repository(run_id, stage_name, "Stage errors not found")
    errors = repository.read_errors(stage_name)
    if errors is None:
        raise HTTPException(status_code=404, detail="Stage errors not found")
    return errors


@router.get("/runs/{run_id}/errors", summary="Get run errors", response_model=list[ErrorResponse], tags=["Run Artifacts"])
def get_run_errors(run_id: str) -> list[JSONPayload]:
    repository = _run_repository(run_id)
    errors = repository.read_errors(run_id)
    if errors is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return errors


@router.get("/runs/{run_id}/metrics", summary="Get run metrics summary", response_model=RunMetricsSummaryResponse, tags=["Run Artifacts"])
def get_run_metrics(run_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    metrics = repository.read_metrics_summary(run_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return metrics


@router.get("/runs/{run_id}", summary="Get run detail", response_model=dict[str, Any], tags=["Run Management"])
def get_run_detail(run_id: str) -> JSONPayload:
    repository = _run_repository(run_id)
    detail = repository.read_detail(run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return detail
