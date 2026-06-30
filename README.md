# Opportunity Intelligence Engine (OIE)

Opportunity Intelligence Engine (OIE) is a modular pipeline for discovering commercial opportunities from job postings.
It provides a FastAPI API to create runs, execute the complete pipeline or individual stages, inspect artifacts, monitor execution, schedule future executions, configure HubSpot delivery metadata, and integrate with external systems.

The project is designed around:

- Independent pipeline stages
- Checkpointing
- Resumability
- Observability
- Deterministic execution
- Explicit artifacts
- API-first operation

---

## Requirements

- Python 3.12+
- pip

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

---

## Run the API Locally

```bash
PYTHONPATH=src python -m uvicorn oie.api.main:app --reload
```

Default local URLs:

| Endpoint | URL |
|---|---|
| API | http://127.0.0.1:8000 |
| Swagger UI | http://127.0.0.1:8000/docs |
| ReDoc | http://127.0.0.1:8000/redoc |
| OpenAPI JSON | http://127.0.0.1:8000/openapi.json |

---

## Pipeline

Current executable staged API pipeline:

```
collect_jobs
    ↓
company_gate
    ↓
freshness_gate
    ↓
domain_gate
```

Current stage mapping:

| `stage_name` | Executes |
|---|---|
| `collect_jobs` | `CollectJobsStage` |
| `company_gate` | `NormalizeJobsStage` |
| `freshness_gate` | `JobIntelligenceStage` |
| `domain_gate` | `CompanyGateStage` |

The complete orchestrated pipeline also includes additional internal steps for company enrichment, scoring, lead generation, persistence, analytics, market outputs, and outbound exports.

---

## Current Pipeline Stage Registry

Defined pipeline stage order:

```
collect_jobs
company_gate
freshness_gate
domain_gate
company_analyzer
icp_match
lead_generation
delivery
company_classification
opportunity_scoring
company_limit
lead_contact_generation
lead_ranking
lead_dedup
snapshot_persistence
opportunity_dataset
opportunity_dataset_export
outbound_export
```

Not every registered stage is independently executable yet. Non-executable stages return:

```json
{
  "detail": "Stage not executable"
}
```

---

## Run Statuses

| Status |
|---|
| `pending` |
| `running` |
| `completed` |
| `partial_success` |
| `failed` |
| `cancelled` |
| `skipped` |
| `waiting_for_user` |
| `company_pipeline_completed` |

---

## API Endpoints

### Health

```
GET /health
```

---

### Runs

```
POST /runs
GET  /runs
GET  /runs/{run_id}
POST /runs/{run_id}/execute
POST /runs/{run_id}/cancel
POST /runs/{run_id}/pause
POST /runs/{run_id}/resume
GET  /runs/{run_id}/status
GET  /runs/{run_id}/configuration
GET  /runs/{run_id}/metrics
GET  /runs/{run_id}/errors
GET  /runs/{run_id}/artifacts
```

---

### Run Scheduling

```
POST /runs/{run_id}/schedule
PUT  /runs/{run_id}/schedule
GET  /runs/{run_id}/schedule
GET  /runs/{run_id}/schedule/status
```

Schedule fields:

| Field | Values |
|---|---|
| `frequency` | `daily`, `weekly`, `monthly` |
| `duration` | e.g. `permanent`, `1 week`, `2 weeks`, `1 month` |
| `scheduled_times` | list of `HH:MM` values |
| `scheduled_days` | optional weekdays |
| `enabled` | boolean |

Example:

```json
{
  "frequency": "weekly",
  "duration": "permanent",
  "scheduled_times": ["09:00", "15:00"],
  "scheduled_days": ["monday", "wednesday"],
  "enabled": true
}
```

---

### HubSpot Delivery

```
PUT /runs/{run_id}/hubspot-delivery
GET /runs/{run_id}/hubspot-delivery
```

Used to persist HubSpot delivery metadata for a run. Sensitive fields such as bearer tokens are not persisted directly in the manifest. Instead, the API stores a credentials reference when needed.

Example:

```json
{
  "hubspot_user_id": "123",
  "hubspot_owner_id": "456",
  "hubspot_company_id": "tekton-company-001",
  "hubspot_credentials_ref": "hubspot/tekton/juan"
}
```

---

### Stage Execution

```
POST /runs/{run_id}/stages/{stage_name}/execute
```

Supported executable stages:

```
collect_jobs
company_gate
freshness_gate
domain_gate
```

A run can also resume from an executable stage using:

```
POST /runs/{run_id}/execute
```

Example body:

```json
{
  "start_stage": "company_gate",
  "rerun": true
}
```

---

### Stage Inspection

```
GET /runs/{run_id}/stages
GET /runs/{run_id}/stages/{stage_name}
GET /runs/{run_id}/stages/{stage_name}/summary
GET /runs/{run_id}/stages/{stage_name}/checkpoint
GET /runs/{run_id}/stages/{stage_name}/metrics
GET /runs/{run_id}/stages/{stage_name}/output
GET /runs/{run_id}/stages/{stage_name}/errors
```

---

## Typical Execution Flow

### 1. Create a run

```bash
curl -X POST http://127.0.0.1:8000/runs \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "runs": {
        "path": "runs"
      }
    },
    "flags": {
      "dry_run": true
    }
  }'
```

### 2. Execute the complete pipeline

```bash
curl -X POST http://127.0.0.1:8000/runs/{run_id}/execute \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 3. Execute from a specific stage

```bash
curl -X POST http://127.0.0.1:8000/runs/{run_id}/execute \
  -H "Content-Type: application/json" \
  -d '{
    "start_stage": "company_gate"
  }'
```

### 4. Rerun from a specific stage

```bash
curl -X POST http://127.0.0.1:8000/runs/{run_id}/execute \
  -H "Content-Type: application/json" \
  -d '{
    "start_stage": "company_gate",
    "rerun": true
  }'
```

### 5. Execute a single stage

```bash
curl -X POST http://127.0.0.1:8000/runs/{run_id}/stages/collect_jobs/execute \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 6. Inspect execution

```
GET /runs/{run_id}
GET /runs/{run_id}/status
GET /runs/{run_id}/configuration
GET /runs/{run_id}/metrics
GET /runs/{run_id}/errors
GET /runs/{run_id}/artifacts
GET /runs/{run_id}/stages
GET /runs/{run_id}/stages/{stage_name}
GET /runs/{run_id}/stages/{stage_name}/summary
GET /runs/{run_id}/stages/{stage_name}/checkpoint
GET /runs/{run_id}/stages/{stage_name}/metrics
GET /runs/{run_id}/stages/{stage_name}/output
GET /runs/{run_id}/stages/{stage_name}/errors
```

---

## Artifacts

The pipeline produces run-level and stage-level artifacts.

### Run-level artifacts

```
manifest.json
configuration.json
commercial_pipeline.csv
commercial.md
apollo_import.csv
hubspot_companies.json
hubspot_contacts.json
hubspot_tasks.json
hubspot_notes.json
hubspot_sync_results.json
companies_export
jobs_export
leads_export
opportunities_export
top_opportunities_export
executive_summary.json
run_readiness_report.json
run_metrics_summary.json
run_analytics.json
historical_company_hiring.csv
historical_growth_summary.csv
historical_summary.json
market_trends_by_source.csv
market_trends_by_location.csv
market_new_companies_by_source.csv
market_trends_summary.json
market_segmented_companies.csv
market_segment_summary.csv
market_segment_summary.json
collector_metrics.json
collector_contribution_metrics.csv
collector_contribution_metrics.json
collector_roi_metrics.csv
collector_roi_metrics.json
provider_operation_metrics.csv
provider_operation_metrics.json
```

### Stage-level artifacts

```
checkpoint.json
metrics.json
output.jsonl
```

---

## Architecture

### API Layer

Located under `src/oie/api/`

Responsibilities:

- Expose FastAPI endpoints
- Validate request and response schemas
- Create runs
- Execute runs
- Execute stages
- Expose run status
- Expose stage artifacts
- Manage schedules
- Manage HubSpot delivery metadata

Main router: `src/oie/api/routers/runs.py`

---

### Orchestration Layer

Located under `src/oie/orchestration/`

Responsibilities:

- Coordinate pipeline execution
- Manage run context
- Resolve run storage
- Manage manifests
- Manage checkpoints
- Execute individual stages
- Expose stage outputs
- Track metrics and errors

Key files:

```
pipeline_orchestrator.py
stage_runner.py
pipeline_stages.py
run_context.py
run_manifest.py
run_repository.py
stage_artifact_repository.py
run_storage_resolver.py
run_schedule.py
```

---

### PipelineOrchestrator

Main orchestrated flow:

```
initialize providers
run company pipeline
select best leads
persist run snapshot and master data
export core reports
export opportunity outputs
build executive summary
export historical outputs
export market outputs
export collector outputs
export provider operation metrics
build readiness and metrics
build run analytics
finalize manifest
build completed result
```

The `run()` method has been reduced by extracting coherent helpers:

```
select_best_leads()
persist_pipeline_data()
export_core_reports()
export_opportunity_outputs()
build_executive_summary()
export_historical_outputs()
export_market_outputs()
export_collector_outputs()
export_provider_operation_metrics()
build_readiness_and_metrics()
build_run_analytics()
build_completed_result()
handle_pipeline_failure()
```

---

### StageRunner

Responsible for executing stage classes with:

- Checkpoint writing
- Metrics writing
- Output writing
- Rerun support
- Error handling
- Resumable execution

---

### Storage Model

Each run has its own run directory. Typical structure:

```
runs/
  {run_id}/
    manifest.json
    configuration.json
    stages/
      collect_jobs/
        checkpoint.json
        metrics.json
        output.jsonl
      company_gate/
        checkpoint.json
        metrics.json
        output.jsonl
      freshness_gate/
        checkpoint.json
        metrics.json
        output.jsonl
      domain_gate/
        checkpoint.json
        metrics.json
        output.jsonl
```

---

### Repository Structure

```
src/oie/
  api/
    main.py
    routers/
      runs.py
    schemas/
      runs.py
  orchestration/
    pipeline_orchestrator.py
    pipeline_stages.py
    stage_runner.py
    stage_base.py
    run_context.py
    run_manifest.py
    run_repository.py
    run_schedule.py
    run_storage_resolver.py
    stage_artifact_repository.py
  services/
    service_provider.py
tests/
  api/
    test_runs.py
  orchestration/
    test_pipeline_orchestrator_smoke.py
    test_pipeline_orchestrator_e2e.py
```

---

## Testing

Run API tests:

```bash
PYTHONPATH=src pytest tests/api -q
```

Run orchestrator tests:

```bash
PYTHONPATH=src pytest tests/orchestration/test_pipeline_orchestrator_smoke.py tests/orchestration/test_pipeline_orchestrator_e2e.py -q
```

Run the focused regression suite used during the refactor:

```bash
PYTHONPATH=src pytest tests/orchestration/test_pipeline_orchestrator_smoke.py tests/orchestration/test_pipeline_orchestrator_e2e.py tests/api/test_runs.py -q
```

Run all tests:

```bash
PYTHONPATH=src pytest -q
```

Compile a modified file:

```bash
PYTHONPATH=src python -m py_compile src/oie/orchestration/pipeline_orchestrator.py
```

Compile router:

```bash
PYTHONPATH=src python -m py_compile src/oie/api/routers/runs.py
```

---

## Git Workflow

After a successful change:

```bash
git status --short
git add <modified-files>
git commit -m "<message>"
git push
```

---

## UI Development

CORS is enabled for local UI development.

Allowed origins:

```
http://localhost:3000
http://localhost:5173
http://127.0.0.1:3000
http://127.0.0.1:5173
```

The API is intended to support a future pipeline monitoring UI capable of:

- Creating runs
- Scheduling runs
- Updating schedules
- Configuring HubSpot delivery
- Executing complete pipelines
- Executing individual stages
- Resuming from a selected stage
- Rerunning stages
- Monitoring run status
- Inspecting checkpoints
- Viewing metrics
- Viewing artifact catalogs
- Viewing stage summaries
- Viewing stage outputs
- Viewing stage errors
- Reviewing generated business artifacts

---

## Current Status

### Implemented

- Run creation
- Run listing
- Run detail
- Run execution
- Run execution from selected stage
- Individual stage execution
- Stage rerun support
- Run cancellation
- Run pause
- Run resume
- Run status
- Run configuration snapshot
- Run metrics
- Run errors
- Run scheduling create/update/read
- Run schedule status
- HubSpot delivery configuration
- Stage status
- Stage list
- Stage checkpoints
- Stage metrics
- Stage output
- Stage errors
- Stage artifact summary
- Artifact catalog
- OpenAPI documentation
- Swagger
- ReDoc
- CORS for local UI
- Orchestrator refactor into smaller helpers
- Focused test coverage for API and orchestrator behavior

---

## Recently Completed Refactor

The pipeline orchestrator was refactored to reduce the size and complexity of `PipelineOrchestrator.run()` without changing behavior.

Completed extractions:

```
artifact_paths_payload()
select_best_leads()
persist_pipeline_data()
export_core_reports()
export_opportunity_outputs()
export_historical_outputs()
export_market_outputs()
export_collector_outputs()
export_provider_operation_metrics()
build_readiness_and_metrics()
build_run_analytics()
build_executive_summary()
build_completed_result()
handle_pipeline_failure()
```

Validation suite used:

```bash
PYTHONPATH=src python -m py_compile src/oie/orchestration/pipeline_orchestrator.py
PYTHONPATH=src pytest tests/orchestration/test_pipeline_orchestrator_smoke.py tests/orchestration/test_pipeline_orchestrator_e2e.py tests/api/test_runs.py -q
```

Latest confirmed result: **80 passed**

---

## Next Planned Work

Recommended next sequence:

1. Finish README commit and freeze this refactor baseline.
2. Add a version tag.
3. Continue with new endpoints and product capabilities only after the baseline is stable.
4. Expand independently executable stages.
5. Add UI-oriented endpoints where needed.
6. Add ICP profile management.
7. Add configurable ICPs per service line.
8. Add incremental company persistence across runs.
9. Add historical company/opportunity intelligence.
10. Add HubSpot/Apollo awareness to avoid duplicate commercial work.
11. Add scheduler daemon or worker process.
12. Add artifact versioning.
13. Add UI dashboard for the commercial team.

---

## Suggested Freeze Command

```bash
git status --short
git add README.md
git commit -m "update project readme after orchestrator refactor"
git push
git tag v0.1.0-refactor-baseline
git push origin v0.1.0-refactor-baseline
```
