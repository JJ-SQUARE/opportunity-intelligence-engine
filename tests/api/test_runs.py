from fastapi.testclient import TestClient

from oie.api.main import app
from oie.orchestration.run_context import RunContext
from oie.orchestration.run_manifest import build_initial_manifest, write_manifest


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

    monkeypatch.setattr("oie.api.main.RunContext.create", fake_create)

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

    monkeypatch.setattr("oie.api.main.RunContext.create", fake_create)

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

    monkeypatch.setattr("oie.api.main.RunContext.create", fake_create)

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

    monkeypatch.setattr("oie.api.main.RunContext.create", fake_create)

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

    monkeypatch.setattr("oie.api.main.RunContext.create", fake_create)

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

    monkeypatch.setattr("oie.api.main.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get(f"/runs/{ctx.run_id}/stages")

    assert response.status_code == 200
    assert response.json()[0] == {"stage": "collect_jobs", "status": "pending"}
    assert response.json()[-1] == {"stage": "delivery", "status": "pending"}


def test_get_run_stages_returns_404_for_missing_run(tmp_path, monkeypatch):
    runs_path = tmp_path / "runs"
    original_create = RunContext.create

    def fake_create(config=None, flags=None, mode=None):
        return original_create(
            config={"runs": {"path": str(runs_path)}},
            flags=flags,
            mode=mode,
        )

    monkeypatch.setattr("oie.api.main.RunContext.create", fake_create)

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

    monkeypatch.setattr("oie.api.main.RunContext.create", fake_create)

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

    monkeypatch.setattr("oie.api.main.RunContext.create", fake_create)

    client = TestClient(app)
    response = client.get("/runs/missing_run/errors")

    assert response.status_code == 404
    assert response.json() == {"detail": "Run not found"}
