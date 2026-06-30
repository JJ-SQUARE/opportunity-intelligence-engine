from fastapi.testclient import TestClient

from oie.api.main import app
from oie.orchestration.run_context import RunContext
from oie.orchestration.run_manifest import build_initial_manifest, finalize_manifest, read_run_manifest, write_manifest


def test_cors_allows_local_ui_origin():
    client = TestClient(app)

    response = client.options(
        "/runs",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_openapi_documents_run_routes():
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Opportunity Intelligence Engine API"
    assert schema["info"]["version"] == "0.1.0"
    assert schema["paths"]["/runs"]["post"]["summary"] == "Create run"
    assert schema["paths"]["/runs"]["get"]["summary"] == "List runs"
    assert schema["paths"]["/runs/{run_id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["type"] == "object"
    assert schema["paths"]["/runs/{run_id}/status"]["get"]["summary"] == "Get run status"
    assert schema["paths"]["/runs/{run_id}/schedule"]["post"]["summary"] == "Create run schedule"
    assert schema["paths"]["/runs/{run_id}/schedule"]["put"]["summary"] == "Update run schedule"
    assert schema["paths"]["/runs/{run_id}/schedule"]["get"]["summary"] == "Get run schedule"
    assert schema["paths"]["/runs/{run_id}/schedule/status"]["get"]["summary"] == "Get run schedule status"
    assert schema["paths"]["/runs/{run_id}/hubspot-delivery"]["put"]["summary"] == "Update run HubSpot delivery"
    assert schema["paths"]["/runs/{run_id}/artifacts"]["get"]["summary"] == "Get artifact catalog"
    assert schema["paths"]["/runs/{run_id}/stages/{stage_name}/output"]["get"]["summary"] == "Get stage output"
    assert schema["paths"]["/runs/{run_id}/stages/{stage_name}/summary"]["get"]["summary"] == "Get stage artifact summary"
    assert schema["paths"]["/runs/{run_id}/stages/{stage_name}/execute"]["post"]["summary"] == "Execute run stage"
    assert schema["paths"]["/runs/{run_id}/stages/{stage_name}/output"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["type"] == "array"
    assert schema["paths"]["/health"]["get"]["tags"] == ["Health"]
    assert "HealthResponse" in schema["components"]["schemas"]
    assert "RunSummaryResponse" in schema["components"]["schemas"]
    assert "RunStatusResponse" in schema["components"]["schemas"]
    assert "CreateRunResponse" in schema["components"]["schemas"]
    assert "RunExecutionResponse" in schema["components"]["schemas"]
    assert "RunStageStatusResponse" in schema["components"]["schemas"]
    assert "RunMetricsSummaryResponse" in schema["components"]["schemas"]
    assert "RunScheduleStatusResponse" in schema["components"]["schemas"]
    assert "HubSpotDeliveryRequest" in schema["components"]["schemas"]
    assert "HubSpotDeliveryResponse" in schema["components"]["schemas"]
    assert "ErrorResponse" in schema["components"]["schemas"]
    assert "HTTPErrorResponse" in schema["components"]["schemas"]
    assert schema["paths"]["/runs/{run_id}"]["get"]["responses"]["404"]["content"]["application/json"]["schema"]["$ref"].endswith("/HTTPErrorResponse")
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
            "account": {},
            "user": {},
            "hubspot_delivery": {},
        }
    ]



def test_list_runs_filters_by_account_id_and_user_id(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"

    ctx_1 = RunContext.create(
        config={
            "runs": {"path": str(runs_path)},
            "account": {"account_id": "tekton"},
            "user": {"user_id": "juan"},
        }
    )
    ctx_2 = RunContext.create(
        config={
            "runs": {"path": str(runs_path)},
            "account": {"account_id": "tekton"},
            "user": {"user_id": "ana"},
        }
    )
    ctx_3 = RunContext.create(
        config={
            "runs": {"path": str(runs_path)},
            "account": {"account_id": "other"},
            "user": {"user_id": "juan"},
        }
    )

    write_manifest(ctx_1, build_initial_manifest(ctx_1))
    write_manifest(ctx_2, build_initial_manifest(ctx_2))
    write_manifest(ctx_3, build_initial_manifest(ctx_3))

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get("/runs?account_id=tekton&user_id=juan")

    assert response.status_code == 200
    payload = response.json()
    assert [item["run_id"] for item in payload] == [ctx_1.run_id]
    assert payload[0]["account"] == {"account_id": "tekton"}
    assert payload[0]["user"] == {"user_id": "juan"}
    assert payload[0]["hubspot_delivery"] == {}


def test_create_run_persists_account_user_and_hubspot_delivery_metadata(tmp_path):
    runs_path = tmp_path / "runs"
    client = TestClient(app)

    response = client.post(
        "/runs",
        json={
            "config": {
                "runs": {"path": str(runs_path)},
                "account": {
                    "account_id": "tekton",
                    "account_name": "Tekton Labs",
                },
                "user": {
                    "user_id": "juan",
                    "email": "juan@example.com",
                },
                "hubspot_delivery": {
                    "hubspot_user_id": "123",
                    "hubspot_owner_id": "456",
                    "hubspot_company_id": "tekton-company-001",
                    "hubspot_credentials_ref": "hubspot/tekton/juan",
                    "hubspot_bearer_token": "secret-token",
                },
            },
            "flags": {"dry_run": True},
        },
    )

    assert response.status_code == 200
    run_id = response.json()["run_id"]
    manifest_path = runs_path / run_id / "manifest.json"

    import json

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["account"] == {
        "account_id": "tekton",
        "account_name": "Tekton Labs",
    }
    assert manifest["user"] == {
        "user_id": "juan",
        "email": "juan@example.com",
    }
    assert manifest["hubspot_delivery"] == {
        "hubspot_user_id": "123",
        "hubspot_owner_id": "456",
        "hubspot_company_id": "tekton-company-001",
        "hubspot_credentials_ref": "hubspot/tekton/juan",
    }
    assert "hubspot_bearer_token" not in manifest["hubspot_delivery"]


def test_update_run_hubspot_delivery_sanitizes_bearer_token(tmp_path, monkeypatch):
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
    response = client.put(
        f"/runs/{ctx.run_id}/hubspot-delivery",
        json={
            "hubspot_user_id": "123",
            "hubspot_owner_id": "456",
            "hubspot_company_id": "tekton-company-001",
            "hubspot_credentials_ref": "hubspot/tekton/juan",
            "hubspot_bearer_token": "secret-token",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload == {
        "run_id": ctx.run_id,
        "hubspot_delivery": {
            "hubspot_user_id": "123",
            "hubspot_owner_id": "456",
            "hubspot_company_id": "tekton-company-001",
            "hubspot_credentials_ref": "hubspot/tekton/juan",
        },
    }

    detail_response = client.get(f"/runs/{ctx.run_id}")
    assert payload["hubspot_delivery"] == detail_response.json()["hubspot_delivery"]
    assert detail_response.status_code == 200
    hubspot_delivery = detail_response.json()["hubspot_delivery"]
    assert hubspot_delivery["hubspot_credentials_ref"] == "hubspot/tekton/juan"
    assert "hubspot_bearer_token" not in hubspot_delivery


def test_update_run_hubspot_delivery_defaults_credentials_ref_from_account_and_user(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(
        config={
            "runs": {"path": str(runs_path)},
            "account": {"account_id": "tekton"},
            "user": {"user_id": "juan"},
        }
    )
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
    response = client.put(
        f"/runs/{ctx.run_id}/hubspot-delivery",
        json={
            "hubspot_user_id": "123",
            "hubspot_owner_id": "456",
            "hubspot_company_id": "tekton-company-001",
            "hubspot_bearer_token": "secret-token",
        },
    )

    assert response.status_code == 200
    assert response.json()["hubspot_delivery"]["hubspot_credentials_ref"] == "hubspot/tekton/juan"


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



def test_create_and_get_run_schedule_persists_frequency_duration_and_programming(tmp_path, monkeypatch):
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
    schedule_payload = {
        "frequency": "weekly",
        "duration": "permanent",
        "scheduled_times": ["09:00", "15:00"],
        "scheduled_days": ["monday", "wednesday"],
        "enabled": True,
    }

    create_response = client.post(
        f"/runs/{ctx.run_id}/schedule",
        json=schedule_payload,
    )
    get_response = client.get(f"/runs/{ctx.run_id}/schedule")

    assert create_response.status_code == 200
    assert create_response.json() == {"run_id": ctx.run_id, **schedule_payload}
    assert get_response.status_code == 200
    assert get_response.json() == {"run_id": ctx.run_id, **schedule_payload}


def test_create_run_schedule_rejects_invalid_frequency_time_and_day(tmp_path, monkeypatch):
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

    invalid_frequency = client.post(
        f"/runs/{ctx.run_id}/schedule",
        json={
            "frequency": "hourly",
            "duration": "1 month",
            "scheduled_times": ["09:00"],
            "scheduled_days": ["monday"],
        },
    )
    invalid_time = client.post(
        f"/runs/{ctx.run_id}/schedule",
        json={
            "frequency": "weekly",
            "duration": "1 month",
            "scheduled_times": ["25:00"],
            "scheduled_days": ["monday"],
        },
    )
    invalid_day = client.post(
        f"/runs/{ctx.run_id}/schedule",
        json={
            "frequency": "weekly",
            "duration": "1 month",
            "scheduled_times": ["09:00"],
            "scheduled_days": ["funday"],
        },
    )

    assert invalid_frequency.status_code == 422
    assert invalid_frequency.json() == {"detail": "Invalid schedule frequency: hourly"}
    assert invalid_time.status_code == 422
    assert invalid_time.json() == {"detail": "Invalid scheduled time: 25:00"}
    assert invalid_day.status_code == 422
    assert invalid_day.json() == {"detail": "Invalid scheduled day: funday"}


def test_run_schedule_status_marks_due_when_time_and_day_match(tmp_path):
    from datetime import UTC, datetime

    from oie.orchestration.run_schedule import run_schedule_status, write_run_schedule

    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})

    write_run_schedule(
        ctx,
        {
            "frequency": "weekly",
            "duration": "permanent",
            "scheduled_times": ["09:00"],
            "scheduled_days": ["monday"],
            "enabled": True,
        },
    )

    payload = run_schedule_status(ctx, datetime(2026, 7, 6, 9, 0, tzinfo=UTC))

    assert payload["run_id"] == ctx.run_id
    assert payload["scheduled"] is True
    assert payload["enabled"] is True
    assert payload["due"] is True
    assert payload["frequency"] == "weekly"


def test_update_run_schedule_replaces_existing_schedule(tmp_path, monkeypatch):
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
    create_payload = {
        "frequency": "weekly",
        "duration": "permanent",
        "scheduled_times": ["09:00"],
        "scheduled_days": ["monday"],
        "enabled": True,
    }
    update_payload = {
        "frequency": "daily",
        "duration": "2 weeks",
        "scheduled_times": ["15:00"],
        "scheduled_days": [],
        "enabled": False,
    }

    create_response = client.post(f"/runs/{ctx.run_id}/schedule", json=create_payload)
    update_response = client.put(f"/runs/{ctx.run_id}/schedule", json=update_payload)
    get_response = client.get(f"/runs/{ctx.run_id}/schedule")

    assert create_response.status_code == 200
    assert update_response.status_code == 200
    assert update_response.json() == {"run_id": ctx.run_id, **update_payload}
    assert get_response.status_code == 200
    assert get_response.json() == {"run_id": ctx.run_id, **update_payload}


def test_get_run_schedule_status_returns_due_payload(tmp_path, monkeypatch):
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
    schedule_payload = {
        "frequency": "daily",
        "duration": "permanent",
        "scheduled_times": [],
        "scheduled_days": [],
        "enabled": True,
    }

    create_response = client.post(f"/runs/{ctx.run_id}/schedule", json=schedule_payload)
    status_response = client.get(f"/runs/{ctx.run_id}/schedule/status")

    assert create_response.status_code == 200
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["run_id"] == ctx.run_id
    assert payload["scheduled"] is True
    assert payload["enabled"] is True
    assert payload["due"] is True
    assert payload["frequency"] == "daily"


def test_get_run_schedule_returns_404_when_missing(tmp_path, monkeypatch):
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
    response = client.get(f"/runs/{ctx.run_id}/schedule")

    assert response.status_code == 404
    assert response.json() == {"detail": "Run schedule not found"}


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



def test_get_run_artifact_catalog_returns_stage_artifact_summaries(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)
    checkpoint_path = ctx.paths["stage_dirs"]["collect_jobs"] + "/checkpoint.json"

    from pathlib import Path
    import json

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
    response = client.get(f"/runs/{ctx.run_id}/artifacts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == ctx.run_id
    assert payload["artifacts"][0]["stage"] == "collect_jobs"
    assert payload["artifacts"][0]["has_checkpoint"] is True
    assert payload["artifacts"][0]["status"] == "completed"
    assert payload["artifacts"][-1]["stage"] == "outbound_export"


def test_get_run_stage_artifact_summary_returns_existing_artifact_summary(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)
    checkpoint_path = ctx.paths["stage_dirs"]["collect_jobs"] + "/checkpoint.json"
    metrics_path = ctx.paths["stage_dirs"]["collect_jobs"] + "/metrics.json"
    output_path = ctx.paths["stage_dirs"]["collect_jobs"] + "/output.jsonl"

    from pathlib import Path
    import json

    checkpoint = {
        "run_id": ctx.run_id,
        "stage": "collect_jobs",
        "status": "completed",
        "input_count": 2,
        "processed_count": 2,
        "output_count": 2,
        "rejected_count": 0,
        "last_processed_index": 1,
        "last_processed_id": "item_2",
        "errors": [],
        "provider_usage": {},
        "cost_estimate": {},
        "processing_time_seconds": 0.1,
    }
    metrics = {
        "run_id": ctx.run_id,
        "stage": "collect_jobs",
        "status": "completed",
        "input_count": 2,
        "processed_count": 2,
        "output_count": 2,
        "rejected_count": 0,
        "error_count": 0,
        "provider_usage": {},
        "cost_estimate": {},
        "processing_time_seconds": 0.1,
    }

    Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
    Path(checkpoint_path).write_text(json.dumps(checkpoint), encoding="utf-8")
    Path(metrics_path).write_text(json.dumps(metrics), encoding="utf-8")
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
    response = client.get(f"/runs/{ctx.run_id}/stages/collect_jobs/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == ctx.run_id
    assert payload["stage"] == "collect_jobs"
    assert payload["has_checkpoint"] is True
    assert payload["has_metrics"] is True
    assert payload["has_output"] is True
    assert payload["status"] == "completed"
    assert payload["input_count"] == 2
    assert payload["processed_count"] == 2
    assert payload["output_count"] == 2
    assert payload["error_count"] == 0
    assert payload["artifact_paths"]["checkpoint"].endswith("checkpoint.json")
    assert payload["artifact_paths"]["metrics"].endswith("metrics.json")
    assert payload["artifact_paths"]["output"].endswith("output.jsonl")


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


def test_execute_collect_jobs_stage_writes_checkpoint_and_output(tmp_path, monkeypatch):
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

    monkeypatch.setattr(
        "oie.orchestration.collect_jobs_stage.CollectionService.collect",
        lambda self: [
            {
                "job_id": "job_1",
                "title": "Backend Engineer",
                "company": "Acme",
                "source": "test",
                "job_url": "https://example.com/jobs/1",
            }
        ],
    )

    client = TestClient(app)
    response = client.post(
        f"/runs/{ctx.run_id}/stages/collect_jobs/execute",
        json={"config": {"runs": {"path": str(runs_path)}}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == ctx.run_id
    assert payload["stage"] == "collect_jobs"
    assert payload["status"] == "completed"
    assert payload["input_count"] == 1
    assert payload["output_count"] == 1

    output_response = client.get(f"/runs/{ctx.run_id}/stages/collect_jobs/output")
    assert output_response.status_code == 200
    assert output_response.json()[0]["id"] == "job_1"
    assert output_response.json()[0]["value"]["company"] == "Acme"


def test_execute_stage_with_rerun_resets_previous_output(tmp_path, monkeypatch):
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

    collected_jobs = [
        {
            "job_id": "job_1",
            "title": "Backend Engineer",
            "company": "Acme",
            "source": "test",
            "job_url": "https://example.com/jobs/1",
        }
    ]

    monkeypatch.setattr(
        "oie.orchestration.collect_jobs_stage.CollectionService.collect",
        lambda self: collected_jobs,
    )

    client = TestClient(app)
    first_response = client.post(
        f"/runs/{ctx.run_id}/stages/collect_jobs/execute",
        json={"config": {"runs": {"path": str(runs_path)}}},
    )
    rerun_response = client.post(
        f"/runs/{ctx.run_id}/stages/collect_jobs/execute",
        json={
            "config": {"runs": {"path": str(runs_path)}},
            "rerun": True,
        },
    )

    assert first_response.status_code == 200
    assert rerun_response.status_code == 200
    assert rerun_response.json()["processed_count"] == 1
    assert rerun_response.json()["output_count"] == 1

    output_response = client.get(f"/runs/{ctx.run_id}/stages/collect_jobs/output")
    assert output_response.status_code == 200
    assert len(output_response.json()) == 1


def test_execute_unknown_stage_returns_404(tmp_path):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    client = TestClient(app)
    response = client.post(
        f"/runs/{ctx.run_id}/stages/lead_generation/execute",
        json={"config": {"runs": {"path": str(runs_path)}}},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Stage not executable"}


def test_execute_run_resumes_from_start_stage(tmp_path, monkeypatch):
    from oie.orchestration.stage_base import Stage

    class ResumeCompanyGateStage(Stage):
        name = "company_gate"
        order = 2

        def load_input(self):
            return [{"id": "company_1", "value": {"company": "Acme"}}]

        def process_item(self, item):
            return {"id": item["id"], "value": item["value"]}

    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    manifest["stages"]["collect_jobs"] = "completed"
    write_manifest(ctx, manifest)

    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.orchestration.run_repository.RunContext.create", fake_create)
    monkeypatch.setitem(
        __import__("oie.api.routers.runs", fromlist=["STAGE_CLASSES"]).STAGE_CLASSES,
        "company_gate",
        ResumeCompanyGateStage,
    )

    client = TestClient(app)
    response = client.post(
        f"/runs/{ctx.run_id}/execute",
        json={
            "config": {"runs": {"path": str(runs_path)}},
            "start_stage": "company_gate",
        },
    )

    assert response.status_code == 200
    assert response.json()["run_id"] == ctx.run_id
    assert response.json()["status"] == "completed"
    assert response.json()["jobs_count"] == 1

    refreshed = read_run_manifest(RunContext.create(config={"runs": {"path": str(runs_path)}}), ctx.run_id)
    assert refreshed["status"] == "completed"
    assert refreshed["stages"]["collect_jobs"] == "completed"
    assert refreshed["stages"]["company_gate"] == "completed"


def test_execute_run_from_unknown_start_stage_returns_404(tmp_path):
    runs_path = tmp_path / "runs"
    ctx = RunContext.create(config={"runs": {"path": str(runs_path)}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    client = TestClient(app)
    response = client.post(
        f"/runs/{ctx.run_id}/execute",
        json={
            "config": {"runs": {"path": str(runs_path)}},
            "start_stage": "unknown_stage",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Stage not found"}


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
