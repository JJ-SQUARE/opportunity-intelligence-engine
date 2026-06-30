from __future__ import annotations

from pathlib import Path

from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.run_context import RunContext
from oie.orchestration.stage_io import read_json_file, write_json_file


def schedule_path(ctx: RunContext) -> Path:
    return Path(ctx.paths["run_dir"]) / "schedule.json"


def write_run_schedule(ctx: RunContext, schedule: JSONPayload) -> JSONPayload:
    payload = {
        "run_id": ctx.run_id,
        "frequency": schedule["frequency"],
        "duration": schedule["duration"],
        "scheduled_times": list(schedule.get("scheduled_times", [])),
        "scheduled_days": list(schedule.get("scheduled_days", [])),
        "enabled": bool(schedule.get("enabled", True)),
    }
    write_json_file(schedule_path(ctx), payload)
    return payload


def read_run_schedule(ctx: RunContext) -> JSONPayload | None:
    return read_json_file(schedule_path(ctx))
