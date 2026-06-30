import pytest

from oie.orchestration.run_context import RunContext
from oie.orchestration.run_manifest import RunManifest, build_initial_manifest, finalize_manifest, list_run_manifests, read_manifest, read_run_manifest, set_run_status, update_stage_status, write_manifest


def test_run_manifest_contract_exposes_required_fields():
    required_keys = set(RunManifest.__annotations__)

    assert required_keys == {
        "run_id",
        "run_date",
        "status",
        "current_stage",
        "created_at",
        "updated_at",
        "mode",
        "config_path",
        "account",
        "user",
        "hubspot_delivery",
        "stages",
        "errors",
    }


def test_read_manifest_returns_existing_manifest(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={"config_path": "config/queries.yaml"},
    )
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    loaded = read_manifest(ctx)

    assert loaded == manifest


def test_read_manifest_returns_none_when_missing(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    assert read_manifest(ctx) is None

def test_read_run_manifest_returns_existing_manifest_by_run_id(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    loaded = read_run_manifest(ctx, ctx.run_id)

    assert loaded == manifest


def test_read_run_manifest_returns_none_for_missing_run_id(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    assert read_run_manifest(ctx, "missing_run") is None


def test_list_run_manifests_returns_existing_manifests(tmp_path):
    ctx_1 = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    ctx_2 = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    write_manifest(ctx_1, build_initial_manifest(ctx_1))
    write_manifest(ctx_2, build_initial_manifest(ctx_2))

    manifests = list_run_manifests(ctx_1)

    assert [manifest["run_id"] for manifest in manifests] == sorted([ctx_1.run_id, ctx_2.run_id])


def test_list_run_manifests_returns_empty_when_runs_dir_missing(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "missing_runs")}},
        flags={},
    )

    assert list_run_manifests(ctx) == []

def test_finalize_manifest_rejects_unknown_status(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    with pytest.raises(ValueError, match="Unknown run status"):
        finalize_manifest(ctx, "unknown_status")


def test_update_stage_status_rejects_unknown_stage(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    with pytest.raises(ValueError, match="Unknown pipeline stage"):
        update_stage_status(ctx, "unknown_stage", "running")


def test_update_stage_status_rejects_unknown_status(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    with pytest.raises(ValueError, match="Unknown run status"):
        update_stage_status(ctx, "collect_jobs", "unknown_status")

def test_set_run_status_updates_manifest_and_returns_status_payload(tmp_path):
    ctx = RunContext.create(config={"runs": {"path": str(tmp_path / "runs")}})
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    result = set_run_status(
        ctx,
        ctx.run_id,
        "waiting_for_user",
        current_stage="collect_jobs",
        error={"error_type": "RuntimeError", "error_message": "pause required"},
    )

    loaded = read_manifest(ctx)

    assert result == {
        "run_id": ctx.run_id,
        "status": "waiting_for_user",
        "current_stage": "collect_jobs",
    }
    assert loaded["status"] == "waiting_for_user"
    assert loaded["current_stage"] == "collect_jobs"
    assert loaded["errors"] == [{"error_type": "RuntimeError", "error_message": "pause required"}]


def test_set_run_status_rejects_unknown_status(tmp_path):
    ctx = RunContext.create(config={"runs": {"path": str(tmp_path / "runs")}})

    with pytest.raises(ValueError, match="Unknown run status"):
        set_run_status(ctx, ctx.run_id, "unknown_status")


def test_next_pending_stage_returns_first_non_completed_stage(tmp_path):
    ctx = RunContext.create(config={"runs": {"path": str(tmp_path / "runs")}})
    manifest = build_initial_manifest(ctx)
    manifest["stages"]["collect_jobs"] = "completed"
    manifest["stages"]["company_gate"] = "completed"

    from oie.orchestration.run_manifest import next_pending_stage

    assert next_pending_stage(manifest) == "freshness_gate"


def test_next_pending_stage_returns_none_when_all_stages_completed(tmp_path):
    ctx = RunContext.create(config={"runs": {"path": str(tmp_path / "runs")}})
    manifest = build_initial_manifest(ctx)
    manifest["stages"] = {stage: "completed" for stage in manifest["stages"]}

    from oie.orchestration.run_manifest import next_pending_stage

    assert next_pending_stage(manifest) is None


def test_next_pending_stage_rejects_unknown_stage_status(tmp_path):
    ctx = RunContext.create(config={"runs": {"path": str(tmp_path / "runs")}})
    manifest = build_initial_manifest(ctx)
    manifest["stages"]["collect_jobs"] = "unknown_status"

    from oie.orchestration.run_manifest import next_pending_stage

    try:
        next_pending_stage(manifest)
    except ValueError as exc:
        assert str(exc) == "Unknown run status: unknown_status"
    else:
        raise AssertionError("Expected ValueError")
