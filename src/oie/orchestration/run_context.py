from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TypedDict
from uuid import uuid4

from oie.models.provider_event import ProviderEventRecord
from oie.orchestration.pipeline_stages import PIPELINE_STAGES


class RunPaths(TypedDict):
    db_path: str
    runs_base_dir: str
    run_dir: str
    manifest_path: str
    stage_dirs: dict[str, str]


@dataclass
class RunContext:
    run_id: str
    run_date: str
    mode: str
    config: dict[str, Any] = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    budgets: dict[str, Any] = field(default_factory=dict)
    provider_events: list[dict[str, Any]] = field(default_factory=list)
    provider_state: dict[str, Any] = field(default_factory=dict)
    paths: RunPaths = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        config: dict[str, Any] | None = None,
        flags: dict[str, Any] | None = None,
        mode: str | None = None,
    ) -> "RunContext":
        config = config or {}
        flags = flags or {}

        if mode is None:
            if flags.get("cache_only"):
                resolved_mode = "cache-only"
            elif flags.get("dry_run"):
                resolved_mode = "dry-run"
            else:
                resolved_mode = "default"
        else:
            resolved_mode = mode

        now = datetime.now(UTC)
        run_id = now.strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:8]
        run_date = now.isoformat()

        db_path = config.get("database", {}).get("path", "data/oie.db")
        runs_base_dir = config.get("runs", {}).get("path", "data/runs")
        run_dir = f"{runs_base_dir}/{run_id}"

        return cls(
            run_id=run_id,
            run_date=run_date,
            mode=resolved_mode,
            config=config,
            flags=flags,
            paths={
                "db_path": db_path,
                "runs_base_dir": runs_base_dir,
                "run_dir": run_dir,
                "manifest_path": f"{run_dir}/manifest.json",
                "stage_dirs": {
                    stage: f"{run_dir}/{index:02d}_{stage}"
                    for index, stage in enumerate(PIPELINE_STAGES, start=1)
                },
            },
        )

    def add_provider_event(
        self,
        provider: str,
        event_type: str,
        message: str,
        metadata: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        event_metadata = metadata or {}
        derived_status_code = status_code

        if derived_status_code is None:
            raw_status_code = event_metadata.get("status_code")
            try:
                derived_status_code = int(raw_status_code) if raw_status_code is not None else None
            except Exception:
                derived_status_code = None

        self.provider_events.append(
            ProviderEventRecord(
                provider=provider,
                event_type=event_type,
                status_code=derived_status_code,
                message=message,
                metadata=event_metadata,
            ).to_dict()
        )
