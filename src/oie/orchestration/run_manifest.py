from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict

from oie.orchestration.pipeline_stages import PIPELINE_STAGES


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
