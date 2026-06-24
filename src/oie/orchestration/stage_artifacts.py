from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict


class StageArtifactPaths(TypedDict):
    stage_dir: Path
    output: Path
    checkpoint: Path
    metrics: Path


def stage_artifact_paths(ctx: Any, stage_name: str) -> StageArtifactPaths:
    stage_dirs = ctx.paths.get("stage_dirs") or {}
    stage_dir = stage_dirs.get(stage_name)
    if not stage_dir:
        raise KeyError(f"Stage dir not configured for stage: {stage_name}")

    base_path = Path(stage_dir)
    return {
        "stage_dir": base_path,
        "output": base_path / "output.jsonl",
        "checkpoint": base_path / "checkpoint.json",
        "metrics": base_path / "metrics.json",
    }


def ensure_stage_dir(ctx: Any, stage_name: str) -> Path:
    paths = stage_artifact_paths(ctx, stage_name)
    stage_dir = paths["stage_dir"]
    stage_dir.mkdir(parents=True, exist_ok=True)
    return stage_dir
