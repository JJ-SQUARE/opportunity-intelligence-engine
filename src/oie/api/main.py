from __future__ import annotations

from fastapi import FastAPI, HTTPException

from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.run_context import RunContext
from oie.orchestration.run_manifest import list_run_summaries, read_run_detail, read_run_stage_statuses, read_run_status

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


@app.get("/runs/{run_id}")
def get_run_detail(run_id: str) -> JSONPayload:
    ctx = RunContext.create()
    detail = read_run_detail(ctx, run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return detail
