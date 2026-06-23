from oie.orchestration.run_context import RunContext
from oie.orchestration.run_manifest import build_initial_manifest, build_run_detail, build_run_errors, build_run_metrics_summary, build_run_status, build_run_summary, build_stage_status, build_stage_statuses, list_run_manifests, list_run_summaries, read_manifest, read_run_detail, read_run_errors, read_run_manifest, read_run_metrics_summary, read_run_stage_status, read_run_stage_statuses, read_run_status, write_manifest


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


def test_build_run_summary_returns_compact_manifest_fields(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    manifest = build_initial_manifest(ctx)

    summary = build_run_summary(manifest)

    assert summary == {
        "run_id": manifest["run_id"],
        "status": manifest["status"],
        "current_stage": manifest["current_stage"],
        "created_at": manifest["created_at"],
        "updated_at": manifest["updated_at"],
    }


def test_list_run_summaries_returns_compact_run_list(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    write_manifest(ctx, build_initial_manifest(ctx))

    summaries = list_run_summaries(ctx)

    assert summaries == [build_run_summary(read_run_manifest(ctx, ctx.run_id))]


def test_build_run_detail_returns_full_manifest_copy(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    manifest = build_initial_manifest(ctx)

    detail = build_run_detail(manifest)

    assert detail == manifest
    assert detail is not manifest


def test_read_run_detail_returns_existing_detail_by_run_id(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    detail = read_run_detail(ctx, ctx.run_id)

    assert detail == manifest


def test_read_run_detail_returns_none_for_missing_run_id(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    assert read_run_detail(ctx, "missing_run") is None


def test_build_run_status_returns_current_status_fields(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    manifest = build_initial_manifest(ctx)

    status = build_run_status(manifest)

    assert status == {
        "run_id": manifest["run_id"],
        "status": manifest["status"],
        "current_stage": manifest["current_stage"],
    }


def test_read_run_status_returns_existing_status_by_run_id(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    status = read_run_status(ctx, ctx.run_id)

    assert status == build_run_status(manifest)


def test_read_run_status_returns_none_for_missing_run_id(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    assert read_run_status(ctx, "missing_run") is None


def test_build_stage_statuses_returns_stage_status_list(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    manifest = build_initial_manifest(ctx)

    statuses = build_stage_statuses(manifest)

    assert statuses[0] == {"stage": "collect_jobs", "status": "pending"}
    assert statuses[-1] == {"stage": "delivery", "status": "pending"}


def test_read_run_stage_statuses_returns_existing_stage_statuses(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    statuses = read_run_stage_statuses(ctx, ctx.run_id)

    assert statuses == build_stage_statuses(manifest)


def test_read_run_stage_statuses_returns_none_for_missing_run_id(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    assert read_run_stage_statuses(ctx, "missing_run") is None


def test_build_stage_status_returns_single_stage_status(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    manifest = build_initial_manifest(ctx)

    status = build_stage_status(manifest, "collect_jobs")

    assert status == {"stage": "collect_jobs", "status": "pending"}


def test_build_stage_status_returns_none_for_unknown_stage(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    manifest = build_initial_manifest(ctx)

    assert build_stage_status(manifest, "unknown_stage") is None


def test_read_run_stage_status_returns_existing_stage_status(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    status = read_run_stage_status(ctx, ctx.run_id, "delivery")

    assert status == {"stage": "delivery", "status": "pending"}


def test_read_run_stage_status_returns_none_for_missing_run_id(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    assert read_run_stage_status(ctx, "missing_run", "collect_jobs") is None


def test_read_run_stage_status_returns_none_for_unknown_stage(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    assert read_run_stage_status(ctx, ctx.run_id, "unknown_stage") is None


def test_build_run_errors_returns_manifest_errors_copy(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    manifest = build_initial_manifest(ctx)
    manifest["errors"].append({"error_type": "RuntimeError", "error_message": "boom"})

    errors = build_run_errors(manifest)

    assert errors == manifest["errors"]
    assert errors is not manifest["errors"]


def test_build_run_errors_returns_empty_when_missing_errors(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    manifest = build_initial_manifest(ctx)
    manifest.pop("errors")

    assert build_run_errors(manifest) == []


def test_read_run_errors_returns_existing_errors_by_run_id(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    manifest = build_initial_manifest(ctx)
    manifest["errors"].append({"error_type": "RuntimeError", "error_message": "boom"})
    write_manifest(ctx, manifest)

    errors = read_run_errors(ctx, ctx.run_id)

    assert errors == build_run_errors(manifest)


def test_read_run_errors_returns_none_for_missing_run_id(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    assert read_run_errors(ctx, "missing_run") is None


def test_build_run_metrics_summary_returns_status_counts(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    manifest = build_initial_manifest(ctx)
    manifest["stages"]["collect_jobs"] = "completed"
    manifest["stages"]["company_gate"] = "running"
    manifest["errors"].append({"error_type": "RuntimeError", "error_message": "boom"})

    summary = build_run_metrics_summary(manifest)

    assert summary["run_id"] == manifest["run_id"]
    assert summary["stage_count"] == len(manifest["stages"])
    assert summary["error_count"] == 1
    assert summary["status_counts"]["completed"] == 1
    assert summary["status_counts"]["running"] == 1
    assert summary["status_counts"]["pending"] == len(manifest["stages"]) - 2


def test_read_run_metrics_summary_returns_existing_summary_by_run_id(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )
    manifest = build_initial_manifest(ctx)
    write_manifest(ctx, manifest)

    summary = read_run_metrics_summary(ctx, ctx.run_id)

    assert summary == build_run_metrics_summary(manifest)


def test_read_run_metrics_summary_returns_none_for_missing_run_id(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    assert read_run_metrics_summary(ctx, "missing_run") is None

