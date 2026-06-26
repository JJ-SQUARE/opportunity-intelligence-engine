from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="Opportunity Intelligence Engine API")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
