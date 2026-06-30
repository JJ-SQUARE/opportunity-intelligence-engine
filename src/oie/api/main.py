from __future__ import annotations

from fastapi import FastAPI

from oie.api.routers.runs import router as runs_router

app = FastAPI(
    title="Opportunity Intelligence Engine API",
    description="API for creating, executing, monitoring, and inspecting OIE pipeline runs.",
    version="0.1.0",
    openapi_tags=[
        {
            "name": "Runs",
            "description": "Run lifecycle, status, stages, metrics, outputs, and errors.",
        },
        {
            "name": "Health",
            "description": "Service health checks.",
        },
    ],
)
app.include_router(runs_router)


@app.get("/health", tags=["Health"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
