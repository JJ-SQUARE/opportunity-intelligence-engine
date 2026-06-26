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
