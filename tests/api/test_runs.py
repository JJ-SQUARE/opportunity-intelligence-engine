from fastapi.testclient import TestClient

from oie.api.main import app
from oie.orchestration.run_context import RunContext
from oie.orchestration.run_manifest import build_initial_manifest, finalize_manifest, read_run_manifest, write_manifest


def test_openapi_documents_run_routes():
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Opportunity Intelligence Engine API"
    assert schema["info"]["version"] == "0.1.0"
    assert schema["paths"]["/runs"]["post"]["summary"] == "Create run"
    assert schema["paths"]["/runs"]["get"]["summary"] == "List runs"
    assert schema["paths"]["/runs/{run_id}/status"]["get"]["summary"] == "Get run status"
    assert schema["paths"]["/runs/{run_id}/stages/{stage_name}/output"]["get"]["summary"] == "Get stage output"
    assert schema["paths"]["/health"]["get"]["tags"] == ["Health"]
    assert "RunSummaryResponse" in schema["components"]["schemas"]
    assert "RunStatusResponse" in schema["components"]["schemas"]
    assert "CreateRunResponse" in schema["components"]["schemas"]
    assert "RunExecutionResponse" in schema["components"]["schemas"]
    assert "RunStageStatusResponse" in schema["components"]["schemas"]
    assert "RunMetricsSummaryResponse" in schema["components"]["schemas"]
    assert "ErrorResponse" in schema["components"]["schemas"]
    assert "StageCheckpointResponse" in schema["components"]["schemas"]
    assert "StageMetricsResponse" in schema["components"]["schemas"]


def test_list_runs_returns_existing_run_summaries(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get("/runs")

    assert response.status_code == 200
    assert response.json() == [
        {
            "run_id": manifest["run_id"],
            "status": manifest["status"],
            "current_stage": manifest["current_stage"],
            "created_at": manifest["created_at"],
            "updated_at": manifest["updated_at"],
        }
    ]



def test_get_run_detail_returns_existing_manifest(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}")

    assert response.status_code == 200
    assert response.json() == manifest


def test_get_run_detail_returns_404_for_missing_run(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get("/runs/missing_run")

    assert response.status_code == 404
    assert response.json() == {"detail": "Run not found"}



def test_get_run_status_returns_existing_status(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/status")

    assert response.status_code == 200
    assert response.json() == {
        "run_id": manifest["run_id"],
        "status": manifest["status"],
        "current_stage": manifest["current_stage"],
    }


def test_get_run_status_returns_404_for_missing_run(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get("/runs/missing_run/status")

    assert response.status_code == 404
    assert response.json() == {"detail": "Run not found"}



def test_get_run_stages_returns_existing_stage_statuses(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/stages")

    assert response.status_code == 200
    assert response.json()[0] == {"stage": "collect_jobs", "status": "pending"}
    assert response.json()[-1] == {"stage": "outbound_export", "status": "pending"}


def test_get_run_stages_returns_404_for_missing_run(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get("/runs/missing_run/stages")

    assert response.status_code == 404
    assert response.json() == {"detail": "Run not found"}



def test_get_run_errors_returns_existing_errors(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    manifest["errors"].append({"error_type": "RuntimeError", "error_message": "boom"})
    write_manifest(ctx, manifest)

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/errors")

    assert response.status_code == 200
    assert response.json() == [{"error_type": "RuntimeError", "error_message": "boom"}]


def test_get_run_errors_returns_404_for_missing_run(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get("/runs/missing_run/errors")

    assert response.status_code == 404
    assert response.json() == {"detail": "Run not found"}



def test_get_run_metrics_returns_existing_metrics_summary(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    manifest["stages"]["collect_jobs"] = "completed"
    manifest["errors"].append({"error_type": "RuntimeError", "error_message": "boom"})
    write_manifest(ctx, manifest)

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/metrics")

    assert response.status_code == 200
    assert response.json() == {
        "run_id": manifest["run_id"],
        "stage_count": len(manifest["stages"]),
        "error_count": 1,
        "status_counts": {
            "completed": 1,
            "pending": len(manifest["stages"]) - 1,
        },
    }


def test_get_run_metrics_returns_404_for_missing_run(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get("/runs/missing_run/metrics")

    assert response.status_code == 404
    assert response.json() == {"detail": "Run not found"}



def test_get_run_stage_returns_existing_stage_status(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/stages/collect_jobs")

    assert response.status_code == 200
    assert response.json() == {"stage": "collect_jobs", "status": "pending"}


def test_get_run_stage_returns_404_for_unknown_stage(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/stages/unknown_stage")

    assert response.status_code == 404
    assert response.json() == {"detail": "Stage not found"}


def test_get_run_stage_returns_404_for_missing_run(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get("/runs/missing_run/stages/collect_jobs")

    assert response.status_code == 404
    assert response.json() == {"detail": "Stage not found"}



def test_get_run_stage_checkpoint_returns_existing_checkpoint(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)
    checkpoint_path = ctx.paths["stage_dirs"]["collect_jobs"] + "/checkpoint.json"
    checkpoint = {
        "run_id": ctx.run_id,
        "stage": "collect_jobs",
        "status": "completed",
        "input_count": 1,
        "processed_count": 1,
        "output_count": 1,
        "rejected_count": 0,
        "last_processed_index": 0,
        "last_processed_id": "item_1",
        "errors": [],
        "provider_usage": {},
        "cost_estimate": {},
        "processing_time_seconds": 0.1,
    }

    from pathlib import Path
    import json

    Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
    Path(checkpoint_path).write_text(json.dumps(checkpoint), encoding="utf-8")

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/stages/collect_jobs/checkpoint")

    assert response.status_code == 200
    assert response.json() == checkpoint


def test_get_run_stage_checkpoint_returns_404_for_missing_checkpoint(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/stages/collect_jobs/checkpoint")

    assert response.status_code == 404
    assert response.json() == {"detail": "Checkpoint not found"}


def test_get_run_stage_checkpoint_returns_404_for_unknown_stage(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/stages/unknown_stage/checkpoint")

    assert response.status_code == 404
    assert response.json() == {"detail": "Checkpoint not found"}


def test_get_run_stage_checkpoint_returns_404_for_missing_run(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get("/runs/missing_run/stages/collect_jobs/checkpoint")

    assert response.status_code == 404
    assert response.json() == {"detail": "Checkpoint not found"}



def test_get_run_stage_metrics_returns_existing_metrics(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)
    metrics_path = ctx.paths["stage_dirs"]["collect_jobs"] + "/metrics.json"
    metrics = {
        "run_id": ctx.run_id,
        "stage": "collect_jobs",
        "status": "completed",
        "input_count": 1,
        "processed_count": 1,
        "output_count": 1,
        "rejected_count": 0,
        "error_count": 0,
        "provider_usage": {},
        "cost_estimate": {},
        "processing_time_seconds": 0.1,
    }

    from pathlib import Path
    import json

    Path(metrics_path).parent.mkdir(parents=True, exist_ok=True)
    Path(metrics_path).write_text(json.dumps(metrics), encoding="utf-8")

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/stages/collect_jobs/metrics")

    assert response.status_code == 200
    assert response.json() == metrics


def test_get_run_stage_metrics_returns_404_for_missing_metrics(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/stages/collect_jobs/metrics")

    assert response.status_code == 404
    assert response.json() == {"detail": "Stage metrics not found"}


def test_get_run_stage_metrics_returns_404_for_unknown_stage(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/stages/unknown_stage/metrics")

    assert response.status_code == 404
    assert response.json() == {"detail": "Stage metrics not found"}


def test_get_run_stage_metrics_returns_404_for_missing_run(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get("/runs/missing_run/stages/collect_jobs/metrics")

    assert response.status_code == 404
    assert response.json() == {"detail": "Stage metrics not found"}



def test_get_run_stage_output_returns_existing_output(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)
    output_path = ctx.paths["stage_dirs"]["collect_jobs"] + "/output.jsonl"

    from pathlib import Path
    import json

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(
        json.dumps({"id": "item_1", "value": 10}) + "\n"
        + json.dumps({"id": "item_2", "value": 20}) + "\n",
        encoding="utf-8",
    )

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/stages/collect_jobs/output")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "item_1", "value": 10},
        {"id": "item_2", "value": 20},
    ]


def test_get_run_stage_output_returns_404_for_missing_output(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/stages/collect_jobs/output")

    assert response.status_code == 404
    assert response.json() == {"detail": "Stage output not found"}


def test_get_run_stage_output_returns_404_for_unknown_stage(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/stages/unknown_stage/output")

    assert response.status_code == 404
    assert response.json() == {"detail": "Stage output not found"}


def test_get_run_stage_output_returns_404_for_missing_run(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get("/runs/missing_run/stages/collect_jobs/output")

    assert response.status_code == 404
    assert response.json() == {"detail": "Stage output not found"}


def test_get_run_stage_errors_returns_existing_errors(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)
    checkpoint_path = ctx.paths["stage_dirs"]["collect_jobs"] + "/checkpoint.json"
    checkpoint = {
        "run_id": ctx.run_id,
        "stage": "collect_jobs",
        "status": "failed",
        "input_count": 1,
        "processed_count": 0,
        "output_count": 0,
        "rejected_count": 0,
        "last_processed_index": None,
        "last_processed_id": None,
        "errors": [{"error_type": "RuntimeError", "error_message": "boom"}],
        "provider_usage": {},
        "cost_estimate": {},
        "processing_time_seconds": 0.1,
    }

    from pathlib import Path
    import json

    Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
    Path(checkpoint_path).write_text(json.dumps(checkpoint), encoding="utf-8")

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/stages/collect_jobs/errors")

    assert response.status_code == 200
    assert response.json() == [{"error_type": "RuntimeError", "error_message": "boom"}]


def test_get_run_stage_errors_returns_empty_list_when_no_errors(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)
    checkpoint_path = ctx.paths["stage_dirs"]["collect_jobs"] + "/checkpoint.json"
    checkpoint = {
        "run_id": ctx.run_id,
        "stage": "collect_jobs",
        "status": "completed",
        "input_count": 1,
        "processed_count": 1,
        "output_count": 1,
        "rejected_count": 0,
        "last_processed_index": 0,
        "last_processed_id": "item_1",
        "errors": [],
        "provider_usage": {},
        "cost_estimate": {},
        "processing_time_seconds": 0.1,
    }

    from pathlib import Path
    import json

    Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
    Path(checkpoint_path).write_text(json.dumps(checkpoint), encoding="utf-8")

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/stages/collect_jobs/errors")

    assert response.status_code == 200
    assert response.json() == []


def test_get_run_stage_errors_returns_404_for_missing_checkpoint(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/stages/collect_jobs/errors")

    assert response.status_code == 404
    assert response.json() == {"detail": "Stage errors not found"}


def test_get_run_stage_errors_returns_404_for_unknown_stage(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/stages/unknown_stage/errors")

    assert response.status_code == 404
    assert response.json() == {"detail": "Stage errors not found"}


def test_get_run_stage_errors_returns_404_for_missing_run(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get("/runs/missing_run/stages/collect_jobs/errors")

    assert response.status_code == 404
    assert response.json() == {"detail": "Stage errors not found"}


def test_create_run_writes_initial_manifest(tmp_path):
    runs_path = tmp_path / "runs"
    client = TestClient(app)

    response = client.post(
        "/runs",
        json={
            "config": {"runs": {"path": str(runs_path)}},
            "flags": {"dry_run": True},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"]
    assert payload["status"] == "pending"
    assert payload["current_stage"] is None
    assert payload["manifest_path"].endswith("manifest.json")

    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest_path = runs_path / payload["run_id"] / "manifest.json"
    assert manifest_path.exists()


def test_execute_run_runs_existing_manifest(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    class FakePipelineOrchestrator:
        def __init__(self, run_ctx):
            self.ctx = run_ctx

        def run(self):
            finalize_manifest(self.ctx, "completed")
            return {
                "run_id": self.ctx.run_id,
                "status": "completed",
                "jobs_count": 0,
                "companies_count": 0,
                "leads_count": 0,
            }

    monkeypatch.setattr("oie.api.routers.runs.PipelineOrchestrator", FakePipelineOrchestrator)

    client = TestClient(app)
    response = client.post(
        f"/runs/{ctx.run_id}/execute",
        json={"config": {"runs": {"path": str(runs_path)}}},
    )

    assert response.status_code == 200
    assert response.json()["run_id"] == ctx.run_id
    assert response.json()["status"] == "completed"

    updated_manifest = read_run_manifest(ctx, ctx.run_id)
    assert updated_manifest is not None
    assert updated_manifest["status"] == "completed"


def test_execute_run_returns_404_for_missing_run(tmp_path):
    runs_path = tmp_path / "runs"
    client = TestClient(app)

    response = client.post(
        "/runs/missing_run/execute",
        json={"config": {"runs": {"path": str(runs_path)}}},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Run not found"}


def test_cancel_run_marks_existing_manifest_cancelled(tmp_path):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    client = TestClient(app)
    response = client.post(
        f"/runs/{ctx.run_id}/cancel",
        json={"config": {"runs": {"path": str(runs_path)}}},
    )

    assert response.status_code == 200
    assert response.json()["run_id"] == ctx.run_id
    assert response.json()["status"] == "cancelled"

    updated_manifest = read_run_manifest(ctx, ctx.run_id)
    assert updated_manifest is not None
    assert updated_manifest["status"] == "cancelled"


def test_cancel_run_returns_404_for_missing_run(tmp_path):
    runs_path = tmp_path / "runs"
    client = TestClient(app)

    response = client.post(
        "/runs/missing_run/cancel",
        json={"config": {"runs": {"path": str(runs_path)}}},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Run not found"}


def test_pause_run_marks_existing_manifest_waiting_for_user(tmp_path):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    client = TestClient(app)
    response = client.post(
        f"/runs/{ctx.run_id}/pause",
        json={"config": {"runs": {"path": str(runs_path)}}},
    )

    assert response.status_code == 200
    assert response.json()["run_id"] == ctx.run_id
    assert response.json()["status"] == "waiting_for_user"

    updated_manifest = read_run_manifest(ctx, ctx.run_id)
    assert updated_manifest is not None
    assert updated_manifest["status"] == "waiting_for_user"


def test_resume_run_marks_existing_manifest_pending(tmp_path):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    manifest["status"] = "waiting_for_user"
    write_manifest(ctx, manifest)

    client = TestClient(app)
    response = client.post(
        f"/runs/{ctx.run_id}/resume",
        json={"config": {"runs": {"path": str(runs_path)}}},
    )

    assert response.status_code == 200
    assert response.json()["run_id"] == ctx.run_id
    assert response.json()["status"] == "pending"

    updated_manifest = read_run_manifest(ctx, ctx.run_id)
    assert updated_manifest is not None
    assert updated_manifest["status"] == "pending"


def test_pause_run_returns_404_for_missing_run(tmp_path):
    runs_path = tmp_path / "runs"
    client = TestClient(app)

    response = client.post(
        "/runs/missing_run/pause",
        json={"config": {"runs": {"path": str(runs_path)}}},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Run not found"}


def test_resume_run_returns_404_for_missing_run(tmp_path):
    runs_path = tmp_path / "runs"
    client = TestClient(app)

    response = client.post(
        "/runs/missing_run/resume",
        json={"config": {"runs": {"path": str(runs_path)}}},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Run not found"}
