from pathlib import Path

from oie.orchestration.run_context import RunContext
from oie.orchestration.stage_artifacts import ensure_stage_dir, stage_artifact_paths


def test_stage_artifact_paths_resolves_standard_files(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    paths = stage_artifact_paths(ctx, "collect_jobs")

    assert paths["stage_dir"] == Path(ctx.paths["stage_dirs"]["collect_jobs"])
    assert paths["output"] == paths["stage_dir"] / "output.jsonl"
    assert paths["checkpoint"] == paths["stage_dir"] / "checkpoint.json"
    assert paths["metrics"] == paths["stage_dir"] / "metrics.json"


def test_ensure_stage_dir_creates_directory(tmp_path):
    ctx = RunContext.create(
        config={"runs": {"path": str(tmp_path / "runs")}},
        flags={},
    )

    stage_dir = ensure_stage_dir(ctx, "company_gate")

    assert stage_dir.exists()
    assert stage_dir.is_dir()
    assert stage_dir == Path(ctx.paths["stage_dirs"]["company_gate"])
