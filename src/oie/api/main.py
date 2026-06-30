from __future__ import annotations

from fastapi import FastAPI

from oie.api.routers.runs import router as runs_router

app = FastAPI(title="Opportunity Intelligence Engine API")
app.include_router(runs_router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
