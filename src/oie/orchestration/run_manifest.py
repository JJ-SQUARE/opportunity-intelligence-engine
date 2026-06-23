from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict

from oie.orchestration.pipeline_stages import PIPELINE_STAGES
from oie.orchestration.stage_io import read_json_file


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def build_initial_manifest(ctx: Any) -> Dict[str, Any]:
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


def write_manifest(ctx: Any, manifest: Dict[str, Any]) -> Path:
    manifest_path = Path(ctx.paths["manifest_path"])
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        __import__("json").dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest_path


def read_manifest(ctx: Any) -> Dict[str, Any] | None:
    return read_json_file(Path(ctx.paths["manifest_path"]))


def read_run_manifest(ctx: Any, run_id: str) -> Dict[str, Any] | None:
    manifest_path = Path(ctx.paths["runs_base_dir"]) / run_id / "manifest.json"
    return read_json_file(manifest_path)


def list_run_manifests(ctx: Any) -> list[Dict[str, Any]]:
    runs_base_dir = Path(ctx.paths["runs_base_dir"])
    if not runs_base_dir.exists():
        return []

    manifests = []
    for manifest_path in sorted(runs_base_dir.glob("*/manifest.json")):
        manifest = read_json_file(manifest_path)
        if manifest is not None:
            manifests.append(manifest)
    return manifests


def build_run_summary(manifest: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": manifest["run_id"],
        "status": manifest["status"],
        "current_stage": manifest["current_stage"],
        "created_at": manifest["created_at"],
        "updated_at": manifest["updated_at"],
    }


def list_run_summaries(ctx: Any) -> list[Dict[str, Any]]:
    return [build_run_summary(manifest) for manifest in list_run_manifests(ctx)]


def build_run_detail(manifest: Dict[str, Any]) -> Dict[str, Any]:
    return dict(manifest)


def read_run_detail(ctx: Any, run_id: str) -> Dict[str, Any] | None:
    manifest = read_run_manifest(ctx, run_id)
    if manifest is None:
        return None
    return build_run_detail(manifest)


def build_run_status(manifest: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": manifest["run_id"],
        "status": manifest["status"],
        "current_stage": manifest["current_stage"],
    }


def read_run_status(ctx: Any, run_id: str) -> Dict[str, Any] | None:
    manifest = read_run_manifest(ctx, run_id)
    if manifest is None:
        return None
    return build_run_status(manifest)


def build_stage_statuses(manifest: Dict[str, Any]) -> list[Dict[str, Any]]:
    return [
        {"stage": stage_name, "status": status}
        for stage_name, status in manifest.get("stages", {}).items()
    ]


def read_run_stage_statuses(ctx: Any, run_id: str) -> list[Dict[str, Any]] | None:
    manifest = read_run_manifest(ctx, run_id)
    if manifest is None:
        return None
    return build_stage_statuses(manifest)


def build_stage_status(manifest: Dict[str, Any], stage_name: str) -> Dict[str, Any] | None:
    stages = manifest.get("stages", {})
    if stage_name not in stages:
        return None
    return {"stage": stage_name, "status": stages[stage_name]}


def read_run_stage_status(ctx: Any, run_id: str, stage_name: str) -> Dict[str, Any] | None:
    manifest = read_run_manifest(ctx, run_id)
    if manifest is None:
        return None
    return build_stage_status(manifest, stage_name)


def build_run_errors(manifest: Dict[str, Any]) -> list[Dict[str, Any]]:
    return list(manifest.get("errors", []))


def read_run_errors(ctx: Any, run_id: str) -> list[Dict[str, Any]] | None:
    manifest = read_run_manifest(ctx, run_id)
    if manifest is None:
        return None
    return build_run_errors(manifest)


def build_run_metrics_summary(manifest: Dict[str, Any]) -> Dict[str, Any]:
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


def read_run_metrics_summary(ctx: Any, run_id: str) -> Dict[str, Any] | None:
    manifest = read_run_manifest(ctx, run_id)
    if manifest is None:
        return None
    return build_run_metrics_summary(manifest)


def finalize_manifest(ctx: Any, status: str, error: Dict[str, Any] | None = None) -> Path:
    manifest_path = Path(ctx.paths["manifest_path"])
    if manifest_path.exists():
        manifest = __import__("json").loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = build_initial_manifest(ctx)

    manifest["status"] = status
    manifest["updated_at"] = utc_now_iso()
    if error is not None:
        manifest.setdefault("errors", []).append(error)

    return write_manifest(ctx, manifest)


def update_stage_status(ctx: Any, stage_name: str, status: str) -> Path:
    manifest_path = Path(ctx.paths["manifest_path"])
    if manifest_path.exists():
        manifest = __import__("json").loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = build_initial_manifest(ctx)

    manifest["current_stage"] = stage_name
    manifest.setdefault("stages", {})[stage_name] = status
    manifest["updated_at"] = utc_now_iso()
    return write_manifest(ctx, manifest)
