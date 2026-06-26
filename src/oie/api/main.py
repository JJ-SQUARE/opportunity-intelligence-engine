from __future__ import annotations

from fastapi import FastAPI, HTTPException

from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.pipeline_stages import PIPELINE_STAGES
from oie.orchestration.run_context import RunContext
from oie.orchestration.stage_artifacts import stage_artifact_paths
from oie.orchestration.stage_checkpoint import load_checkpoint_payload
from oie.orchestration.stage_io import read_json_file
from oie.orchestration.run_manifest import list_run_summaries, read_run_detail, read_run_errors, read_run_metrics_summary, read_run_stage_status, read_run_stage_statuses, read_run_status

app = FastAPI(title="Opportunity Intelligence Engine API")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/runs")
def list_runs() -> list[JSONPayload]:
    ctx = RunContext.create()
    return list_run_summaries(ctx)


@app.get("/runs/{run_id}/status")
def get_run_status(run_id: str) -> JSONPayload:
    ctx = RunContext.create()
    status = read_run_status(ctx, run_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return status


@app.get("/runs/{run_id}/stages")
def get_run_stages(run_id: str) -> list[JSONPayload]:
    ctx = RunContext.create()
    stages = read_run_stage_statuses(ctx, run_id)
    if stages is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return stages


@app.get("/runs/{run_id}/stages/{stage_name}")
def get_run_stage(run_id: str, stage_name: str) -> JSONPayload:
    ctx = RunContext.create()
    stage = read_run_stage_status(ctx, run_id, stage_name)
    if stage is None:
        raise HTTPException(status_code=404, detail="Stage not found")
    return stage


@app.get("/runs/{run_id}/stages/{stage_name}/checkpoint")
def get_run_stage_checkpoint(run_id: str, stage_name: str) -> JSONPayload:
    ctx = RunContext.create()
    detail = read_run_detail(ctx, run_id)
    if detail is None or stage_name not in PIPELINE_STAGES:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    ctx.paths["run_dir"] = f'{ctx.paths["runs_base_dir"]}/{run_id}'
    ctx.paths["manifest_path"] = f'{ctx.paths["run_dir"]}/manifest.json'
    ctx.paths["stage_dirs"] = {
        stage: f'{ctx.paths["run_dir"]}/{index:02d}_{stage}'
        for index, stage in enumerate(PIPELINE_STAGES, start=1)
    }

    checkpoint = read_json_file(stage_artifact_paths(ctx, stage_name)["checkpoint"])
    if checkpoint is None:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return load_checkpoint_payload(checkpoint)


@app.get("/runs/{run_id}/stages/{stage_name}/metrics")
def get_run_stage_metrics(run_id: str, stage_name: str) -> JSONPayload:
    ctx = RunContext.create()
    detail = read_run_detail(ctx, run_id)
    if detail is None or stage_name not in PIPELINE_STAGES:
        raise HTTPException(status_code=404, detail="Stage metrics not found")

    ctx.paths["run_dir"] = f'{ctx.paths["runs_base_dir"]}/{run_id}'
    ctx.paths["manifest_path"] = f'{ctx.paths["run_dir"]}/manifest.json'
    ctx.paths["stage_dirs"] = {
        stage: f'{ctx.paths["run_dir"]}/{index:02d}_{stage}'
        for index, stage in enumerate(PIPELINE_STAGES, start=1)
    }

    metrics = read_json_file(stage_artifact_paths(ctx, stage_name)["metrics"])
    if metrics is None:
        raise HTTPException(status_code=404, detail="Stage metrics not found")
    return metrics


@app.get("/runs/{run_id}/errors")
def get_run_errors(run_id: str) -> list[JSONPayload]:
    ctx = RunContext.create()
    errors = read_run_errors(ctx, run_id)
    if errors is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return errors


@app.get("/runs/{run_id}/metrics")
def get_run_metrics(run_id: str) -> JSONPayload:
    ctx = RunContext.create()
    metrics = read_run_metrics_summary(ctx, run_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return metrics


@app.get("/runs/{run_id}")
def get_run_detail(run_id: str) -> JSONPayload:
    ctx = RunContext.create()
    detail = read_run_detail(ctx, run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return detail
