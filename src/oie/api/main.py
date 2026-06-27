from __future__ import annotations

from fastapi import FastAPI, HTTPException

from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.pipeline_stages import PIPELINE_STAGES
from oie.orchestration.run_context import RunContext
from oie.orchestration.run_repository import RunRepository
from oie.orchestration.stage_artifact_repository import StageArtifactRepository

app = FastAPI(title="Opportunity Intelligence Engine API")


def _run_repository() -> RunRepository:
    ctx = RunContext.create()
    return RunRepository(ctx)


def _stage_artifact_repository(
    ctx: RunContext,
    run_id: str,
    stage_name: str,
    not_found_detail: str,
) -> StageArtifactRepository:
    repository = RunRepository(ctx)
    detail = repository.read_detail(run_id)
    if detail is None or stage_name not in PIPELINE_STAGES:
        raise HTTPException(status_code=404, detail=not_found_detail)
    return StageArtifactRepository(ctx, run_id)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


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
    ctx = RunContext.create()
    repository = RunRepository(ctx)
    stages = repository.read_stages(run_id)
    if stages is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return stages


@app.get("/runs/{run_id}/stages/{stage_name}")
def get_run_stage(run_id: str, stage_name: str) -> JSONPayload:
    ctx = RunContext.create()
    repository = RunRepository(ctx)
    stage = repository.read_stage(run_id, stage_name)
    if stage is None:
        raise HTTPException(status_code=404, detail="Stage not found")
    return stage


@app.get("/runs/{run_id}/stages/{stage_name}/checkpoint")
def get_run_stage_checkpoint(run_id: str, stage_name: str) -> JSONPayload:
    ctx = RunContext.create()
    repository = _stage_artifact_repository(ctx, run_id, stage_name, "Checkpoint not found")
    checkpoint = repository.read_checkpoint(stage_name)
    if checkpoint is None:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return checkpoint


@app.get("/runs/{run_id}/stages/{stage_name}/metrics")
def get_run_stage_metrics(run_id: str, stage_name: str) -> JSONPayload:
    ctx = RunContext.create()
    repository = _stage_artifact_repository(ctx, run_id, stage_name, "Stage metrics not found")
    metrics = repository.read_metrics(stage_name)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Stage metrics not found")
    return metrics


@app.get("/runs/{run_id}/stages/{stage_name}/output")
def get_run_stage_output(run_id: str, stage_name: str) -> list[JSONPayload]:
    ctx = RunContext.create()
    repository = _stage_artifact_repository(ctx, run_id, stage_name, "Stage output not found")
    output = repository.read_output(stage_name)
    if output is None:
        raise HTTPException(status_code=404, detail="Stage output not found")
    return output


@app.get("/runs/{run_id}/stages/{stage_name}/errors")
def get_run_stage_errors(run_id: str, stage_name: str) -> list[JSONPayload]:
    ctx = RunContext.create()
    repository = _stage_artifact_repository(ctx, run_id, stage_name, "Stage errors not found")
    errors = repository.read_errors(stage_name)
    if errors is None:
        raise HTTPException(status_code=404, detail="Stage errors not found")
    return errors


@app.get("/runs/{run_id}/errors")
def get_run_errors(run_id: str) -> list[JSONPayload]:
    ctx = RunContext.create()
    repository = RunRepository(ctx)
    errors = repository.read_errors(run_id)
    if errors is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return errors


@app.get("/runs/{run_id}/metrics")
def get_run_metrics(run_id: str) -> JSONPayload:
    ctx = RunContext.create()
    repository = RunRepository(ctx)
    metrics = repository.read_metrics_summary(run_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return metrics


@app.get("/runs/{run_id}")
def get_run_detail(run_id: str) -> JSONPayload:
    ctx = RunContext.create()
    repository = RunRepository(ctx)
    detail = repository.read_detail(run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return detail
