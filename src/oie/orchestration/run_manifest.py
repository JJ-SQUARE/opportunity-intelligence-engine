from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.pipeline_stages import PIPELINE_STAGES, validate_pipeline_stage, validate_run_status
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
    account: JSONPayload
    user: JSONPayload
    hubspot_delivery: JSONPayload
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
        "account": dict(ctx.config.get("account", {}) or {}),
        "user": dict(ctx.config.get("user", {}) or {}),
        "hubspot_delivery": {
            key: value
            for key, value in dict(ctx.config.get("hubspot_delivery", {}) or {}).items()
            if key != "hubspot_bearer_token"
        },
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


def next_pending_stage(manifest: RunManifest) -> str | None:
    for stage_name in PIPELINE_STAGES:
        status = manifest.get("stages", {}).get(stage_name, "pending")
        validate_run_status(status)
        if status != "completed":
            return stage_name
    return None


def finalize_manifest(ctx: RunContext, status: str, error: JSONPayload | None = None) -> Path:
    validate_run_status(status)
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
    validate_pipeline_stage(stage_name)
    validate_run_status(status)
    manifest_path = Path(ctx.paths["manifest_path"])
    manifest = read_json_file(manifest_path)
    if manifest is None:
        manifest = build_initial_manifest(ctx)
def set_run_status(ctx, run_id: str, status: str, current_stage: str | None = None, error: dict | None = None):
    from oie.orchestration.pipeline_stages import validate_run_status

    validate_run_status(status)

    manifest_path = Path(ctx.paths["manifest_path"])
    manifest = read_json_file(manifest_path)

    if manifest is None:
        manifest = build_initial_manifest(ctx)

    manifest["status"] = status
    manifest["updated_at"] = utc_now_iso()

    if current_stage is not None:
        manifest["current_stage"] = current_stage

    if error is not None:
        manifest.setdefault("errors", []).append(error)

    return write_manifest(ctx, manifest)


    manifest["current_stage"] = stage_name
    manifest.setdefault("stages", {})[stage_name] = status
    manifest["updated_at"] = utc_now_iso()
    return write_manifest(ctx, manifest)
