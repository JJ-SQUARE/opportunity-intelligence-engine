from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from oie.api.routers.runs import router as runs_router

class HealthResponse(BaseModel):
    status: str


app = FastAPI(
    title="Opportunity Intelligence Engine API",
    description="API for creating, executing, monitoring, and inspecting OIE pipeline runs.",
    version="0.1.0",
    openapi_tags=[
        {
            "name": "Run Management",
            "description": "Run lifecycle, execution, configuration, status, and detail.",
        },
        {
            "name": "Run Scheduling",
            "description": "Run scheduling and schedule readiness status.",
        },
        {
            "name": "CRM Delivery",
            "description": "HubSpot delivery configuration for run outputs.",
        },
        {
            "name": "ICP Configuration",
            "description": "ICP profiles available to score and segment opportunities.",
        },
        {
            "name": "Run Artifacts",
            "description": "Stage status, checkpoints, metrics, outputs, artifacts, and errors.",
        },
        {
            "name": "Health",
            "description": "Service health checks.",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(runs_router)


@app.get("/health", tags=["Health"], response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok")
