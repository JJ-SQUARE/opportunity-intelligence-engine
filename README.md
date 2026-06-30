# Opportunity Intelligence Engine (OIE)

Opportunity Intelligence Engine is a FastAPI-backed pipeline for creating, executing, monitoring, and inspecting opportunity discovery runs.

## Requirements

- Python 3.12+
- pip

Install dependencies:

    python -m pip install -r requirements.txt

## Run the API locally

    PYTHONPATH=src python -m uvicorn oie.api.main:app --reload

Default local URLs:

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

## Current API endpoints

- GET /health
- POST /runs
- POST /runs/{run_id}/execute
- POST /runs/{run_id}/stages/{stage_name}/execute
- POST /runs/{run_id}/cancel
- POST /runs/{run_id}/pause
- POST /runs/{run_id}/resume
- GET /runs
- GET /runs/{run_id}
- GET /runs/{run_id}/status
- GET /runs/{run_id}/metrics
- GET /runs/{run_id}/errors
- GET /runs/{run_id}/stages
- GET /runs/{run_id}/stages/{stage_name}
- GET /runs/{run_id}/stages/{stage_name}/checkpoint
- GET /runs/{run_id}/stages/{stage_name}/metrics
- GET /runs/{run_id}/stages/{stage_name}/output
- GET /runs/{run_id}/stages/{stage_name}/errors

## Quick smoke test

Create a run:

    curl -X POST http://127.0.0.1:8000/runs \
      -H "Content-Type: application/json" \
      -d '{"config": {"runs": {"path": "runs"}}, "flags": {"dry_run": true}}'

List runs:

    curl http://127.0.0.1:8000/runs

## Tests

    PYTHONPATH=src pytest tests/api -q
    PYTHONPATH=src pytest -q

## UI development notes

CORS is enabled for local UI development on:

- http://localhost:3000
- http://localhost:5173
- http://127.0.0.1:3000
- http://127.0.0.1:5173
