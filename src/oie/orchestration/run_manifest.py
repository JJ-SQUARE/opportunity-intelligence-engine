from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.pipeline_stages import PIPELINE_STAGES
from oie.orchestration.run_context import RunContext
from oie.orchestration.stage_io import read_json_file, write_json_file


class RunManifest(TypedDict):
    run_id: str
    run_date: str
    status: str
    current_stage: str | None
    created_at: str
    updated_at: str
    mode: str
    config_path: str | None
    stages: dict[str, str]
    errors: list[JSONPayload]


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def build_initial_manifest(ctx: RunContext) -> RunManifest:
    return {
        "run_id": ctx.run_id,
        "run_date": ctx.run_date,
        "status": "pending",
        "current_stage": None,
        "created_at": ctx.run_date,
        "updated_at": utc_now_iso(),
        "mode": ctx.mode,
        "config_path": ctx.flags.get("config_path"),
        "stages": {stage: "pending" for stage in PIPELINE_STAGES},
        "errors": [],
    }


def write_manifest(ctx: RunContext, manifest: RunManifest) -> Path:
    manifest_path = Path(ctx.paths["manifest_path"])
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_file(manifest_path, manifest)
    return manifest_path


def read_manifest(ctx: RunContext) -> RunManifest | None:
    manifest = read_json_file(Path(ctx.paths["manifest_path"]))
    if manifest is None:
        return None
    return RunManifest(**manifest)


def read_run_manifest(ctx: RunContext, run_id: str) -> RunManifest | None:
    manifest_path = Path(ctx.paths["runs_base_dir"]) / run_id / "manifest.json"
    manifest = read_json_file(manifest_path)
    if manifest is None:
        return None
    return RunManifest(**manifest)


def list_run_manifests(ctx: RunContext) -> list[RunManifest]:
    runs_base_dir = Path(ctx.paths["runs_base_dir"])
    if not runs_base_dir.exists():
        return []

    manifests = []
    for manifest_path in sorted(runs_base_dir.glob("*/manifest.json")):
        manifest = read_json_file(manifest_path)
        if manifest is not None:
            manifests.append(RunManifest(**manifest))
    return manifests


def build_run_summary(manifest: RunManifest) -> JSONPayload:
    return {
        "run_id": manifest["run_id"],
        "status": manifest["status"],
        "current_stage": manifest["current_stage"],
        "created_at": manifest["created_at"],
        "updated_at": manifest["updated_at"],
    }


def build_run_detail(manifest: RunManifest) -> JSONPayload:
    return dict(manifest)


def read_run_detail(ctx: RunContext, run_id: str) -> JSONPayload | None:
    manifest = read_run_manifest(ctx, run_id)
    if manifest is None:
        return None
    return build_run_detail(manifest)


def build_run_status(manifest: RunManifest) -> JSONPayload:
    return {
        "run_id": manifest["run_id"],
        "status": manifest["status"],
        "current_stage": manifest["current_stage"],
    }


def read_run_status(ctx: RunContext, run_id: str) -> JSONPayload | None:
    manifest = read_run_manifest(ctx, run_id)
    if manifest is None:
        return None
    return build_run_status(manifest)


def build_stage_statuses(manifest: RunManifest) -> list[JSONPayload]:
    return [
        {"stage": stage_name, "status": status}
        for stage_name, status in manifest.get("stages", {}).items()
    ]


def read_run_stage_statuses(ctx: RunContext, run_id: str) -> list[JSONPayload] | None:
    manifest = read_run_manifest(ctx, run_id)
    if manifest is None:
        return None
    return build_stage_statuses(manifest)


def build_stage_status(manifest: RunManifest, stage_name: str) -> JSONPayload | None:
    stages = manifest.get("stages", {})
    if stage_name not in stages:
        return None
    return {"stage": stage_name, "status": stages[stage_name]}


def read_run_stage_status(ctx: RunContext, run_id: str, stage_name: str) -> JSONPayload | None:
    manifest = read_run_manifest(ctx, run_id)
    if manifest is None:
        return None
    return build_stage_status(manifest, stage_name)


def build_run_errors(manifest: RunManifest) -> list[JSONPayload]:
    return list(manifest.get("errors", []))


def read_run_errors(ctx: RunContext, run_id: str) -> list[JSONPayload] | None:
    manifest = read_run_manifest(ctx, run_id)
    if manifest is None:
        return None
    return build_run_errors(manifest)


def build_run_metrics_summary(manifest: RunManifest) -> JSONPayload:
    stages = manifest.get("stages", {})
    return {
        "run_id": manifest["run_id"],
        "stage_count": len(stages),
        "error_count": len(manifest.get("errors", [])),
        "status_counts": {
            status: list(stages.values()).count(status)
            for status in sorted(set(stages.values()))
        },
    }


def read_run_metrics_summary(ctx: RunContext, run_id: str) -> JSONPayload | None:
    manifest = read_run_manifest(ctx, run_id)
    if manifest is None:
        return None
    return build_run_metrics_summary(manifest)


def finalize_manifest(ctx: RunContext, status: str, error: JSONPayload | None = None) -> Path:
    manifest_path = Path(ctx.paths["manifest_path"])
    manifest = read_json_file(manifest_path)
    if manifest is None:
        manifest = build_initial_manifest(ctx)

    manifest["status"] = status
    manifest["updated_at"] = utc_now_iso()
    if error is not None:
        manifest.setdefault("errors", []).append(error)

    return write_manifest(ctx, manifest)


def update_stage_status(ctx: RunContext, stage_name: str, status: str) -> Path:
    manifest_path = Path(ctx.paths["manifest_path"])
    manifest = read_json_file(manifest_path)
    if manifest is None:
        manifest = build_initial_manifest(ctx)

    manifest["current_stage"] = stage_name
    manifest.setdefault("stages", {})[stage_name] = status
    manifest["updated_at"] = utc_now_iso()
    return write_manifest(ctx, manifest)
