from __future__ import annotations

from fastapi import FastAPI

from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.run_context import RunContext
from oie.orchestration.run_manifest import list_run_summaries

app = FastAPI(title="Opportunity Intelligence Engine API")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/runs")
def list_runs() -> list[JSONPayload]:
    ctx = RunContext.create()
    return list_run_summaries(ctx)
