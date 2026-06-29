from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.pipeline_orchestrator import PipelineOrchestrator
from oie.orchestration.pipeline_stages import PIPELINE_STAGES
from oie.orchestration.run_manifest import build_initial_manifest, write_manifest
from oie.orchestration.run_repository import RunRepository
from oie.orchestration.run_context import RunConfig, RunFlags, RunContext
from oie.orchestration.stage_artifact_repository import StageArtifactRepository

app = FastAPI(title="Opportunity Intelligence Engine API")


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


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/runs")
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


@app.post("/runs/{run_id}/execute")
def execute_run(run_id: str, request: ExecuteRunRequest) -> JSONPayload:
    ctx = _ctx_for_existing_run(
        run_id=run_id,
        config=request.config,
        flags=request.flags,
        mode=request.mode,
    )
    result = PipelineOrchestrator(ctx).run()
    return dict(result)


@app.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str, request: ExecuteRunRequest) -> JSONPayload:
    return _update_run_status(
        run_id=run_id,
        request=request,
        status="cancelled",
        current_stage=None,
    )


@app.post("/runs/{run_id}/pause")
def pause_run(run_id: str, request: ExecuteRunRequest) -> JSONPayload:
    return _update_run_status(
        run_id=run_id,
        request=request,
        status="waiting_for_user",
    )


@app.post("/runs/{run_id}/resume")
def resume_run(run_id: str, request: ExecuteRunRequest) -> JSONPayload:
    return _update_run_status(
        run_id=run_id,
        request=request,
        status="pending",
    )


@app.get("/runs")
def list_runs() -> list[JSONPayload]:
    repository = _run_repository()
    return repository.list_summaries()


@app.get("/runs/{run_id}/status")
def get_run_status(run_id: str) -> JSONPayload:
    repository = _run_repository()
    status = repository.read_status(run_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return status


@app.get("/runs/{run_id}/stages")
def get_run_stages(run_id: str) -> list[JSONPayload]:
    repository = _run_repository()
    stages = repository.read_stages(run_id)
    if stages is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return stages


@app.get("/runs/{run_id}/stages/{stage_name}")
def get_run_stage(run_id: str, stage_name: str) -> JSONPayload:
    repository = _run_repository()
    stage = repository.read_stage(run_id, stage_name)
    if stage is None:
        raise HTTPException(status_code=404, detail="Stage not found")
    return stage


@app.get("/runs/{run_id}/stages/{stage_name}/checkpoint")
def get_run_stage_checkpoint(run_id: str, stage_name: str) -> JSONPayload:
    repository = _stage_artifact_repository(run_id, stage_name, "Checkpoint not found")
    checkpoint = repository.read_checkpoint(stage_name)
    if checkpoint is None:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return checkpoint


@app.get("/runs/{run_id}/stages/{stage_name}/metrics")
def get_run_stage_metrics(run_id: str, stage_name: str) -> JSONPayload:
    repository = _stage_artifact_repository(run_id, stage_name, "Stage metrics not found")
    metrics = repository.read_metrics(stage_name)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Stage metrics not found")
    return metrics


@app.get("/runs/{run_id}/stages/{stage_name}/output")
def get_run_stage_output(run_id: str, stage_name: str) -> list[JSONPayload]:
    repository = _stage_artifact_repository(run_id, stage_name, "Stage output not found")
    output = repository.read_output(stage_name)
    if output is None:
        raise HTTPException(status_code=404, detail="Stage output not found")
    return output


@app.get("/runs/{run_id}/stages/{stage_name}/errors")
def get_run_stage_errors(run_id: str, stage_name: str) -> list[JSONPayload]:
    repository = _stage_artifact_repository(run_id, stage_name, "Stage errors not found")
    errors = repository.read_errors(stage_name)
    if errors is None:
        raise HTTPException(status_code=404, detail="Stage errors not found")
    return errors


@app.get("/runs/{run_id}/errors")
def get_run_errors(run_id: str) -> list[JSONPayload]:
    repository = _run_repository()
    errors = repository.read_errors(run_id)
    if errors is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return errors


@app.get("/runs/{run_id}/metrics")
def get_run_metrics(run_id: str) -> JSONPayload:
    repository = _run_repository()
    metrics = repository.read_metrics_summary(run_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return metrics


@app.get("/runs/{run_id}")
def get_run_detail(run_id: str) -> JSONPayload:
    repository = _run_repository()
    detail = repository.read_detail(run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return detail
