from __future__ import annotations

from pathlib import Path
import re

from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.run_context import RunContext
from oie.orchestration.stage_io import read_json_file, write_json_file


VALID_FREQUENCIES = {"daily", "weekly", "monthly"}
VALID_DAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
TIME_PATTERN = re.compile(r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
DURATION_PATTERN = re.compile(r"^permanent$|^[1-9]\\d*\\s+(day|days|week|weeks|month|months)$")


def schedule_path(ctx: RunContext) -> Path:
    return Path(ctx.paths["run_dir"]) / "schedule.json"


def validate_run_schedule(schedule: JSONPayload) -> None:
    frequency = str(schedule.get("frequency") or "").strip().lower()
    if frequency not in VALID_FREQUENCIES:
        raise ValueError(f"Invalid schedule frequency: {frequency}")

    duration = str(schedule.get("duration") or "").strip()
    if not DURATION_PATTERN.match(duration):
        raise ValueError(f"Invalid schedule duration: {duration}")

    for scheduled_time in schedule.get("scheduled_times", []):
        value = str(scheduled_time).strip()
        if not TIME_PATTERN.match(value):
            raise ValueError(f"Invalid scheduled time: {value}")

    for scheduled_day in schedule.get("scheduled_days", []):
        value = str(scheduled_day).strip().lower()
        if value not in VALID_DAYS:
            raise ValueError(f"Invalid scheduled day: {value}")


def write_run_schedule(ctx: RunContext, schedule: JSONPayload) -> JSONPayload:
    validate_run_schedule(schedule)
    payload = {
        "run_id": ctx.run_id,
        "frequency": str(schedule["frequency"]).strip().lower(),
        "duration": str(schedule["duration"]).strip(),
        "scheduled_times": [str(value).strip() for value in schedule.get("scheduled_times", [])],
        "scheduled_days": [str(value).strip().lower() for value in schedule.get("scheduled_days", [])],
        "enabled": bool(schedule.get("enabled", True)),
    }
    write_json_file(schedule_path(ctx), payload)
    return payload


def read_run_schedule(ctx: RunContext) -> JSONPayload | None:
    return read_json_file(schedule_path(ctx))
