from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TypedDict
from uuid import uuid4

from oie.models.provider_event import ProviderEventRecord
from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.pipeline_stages import PIPELINE_STAGES
from oie.persistence.database import DatabaseSettings, resolve_database_settings


class DatabaseConfig(TypedDict, total=False):
    path: str


class RunsConfig(TypedDict, total=False):
    path: str


class AccountConfig(TypedDict, total=False):
    account_id: str
    account_name: str


class UserConfig(TypedDict, total=False):
    user_id: str
    email: str


class HubSpotDeliveryConfig(TypedDict, total=False):
    hubspot_user_id: str
    hubspot_owner_id: str
    hubspot_company_id: str
    hubspot_credentials_ref: str


class RunConfig(TypedDict, total=False):
    database: DatabaseConfig
    runs: RunsConfig
    account: AccountConfig
    user: UserConfig
    hubspot_delivery: HubSpotDeliveryConfig


class RunFlags(TypedDict, total=False):
    cache_only: bool
    dry_run: bool
    config_path: str


class RunConfiguration(TypedDict, total=False):
    database: DatabaseConfig
    runs: RunsConfig
    account: AccountConfig
    user: UserConfig
    hubspot_delivery: HubSpotDeliveryConfig
    flags: RunFlags
    mode: str


class RunMetrics(TypedDict, total=False):
    total_processing_time_seconds: float
    total_input_count: int
    total_output_count: int
    total_rejected_count: int


class RunBudgets(TypedDict, total=False):
    total_cost_usd: float


class ProviderState(TypedDict, total=False):
    last_provider: str
    total_requests: int
    total_tokens: int
    total_cost_usd: float


class ProviderEventPayload(TypedDict):
    provider: str
    event_type: str
    status_code: int | None
    message: str | None
    metadata: JSONPayload


class RunPaths(TypedDict):
    database: DatabaseSettings
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
    config: RunConfig = field(default_factory=dict)
    flags: RunFlags = field(default_factory=dict)
    metrics: RunMetrics = field(default_factory=dict)
    budgets: RunBudgets = field(default_factory=dict)
    provider_events: list[ProviderEventPayload] = field(default_factory=list)
    provider_state: ProviderState = field(default_factory=dict)
    paths: RunPaths = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        config: RunConfig | None = None,
        flags: RunFlags | None = None,
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

        database_settings = resolve_database_settings(config)
        db_path = database_settings.path or "data/oie.db"
        runs_base_dir = config.get("runs", {}).get("path", "data/runs")
        run_dir = f"{runs_base_dir}/{run_id}"

        return cls(
            run_id=run_id,
            run_date=run_date,
            mode=resolved_mode,
            config=config,
            flags=flags,
            paths={
                "database": database_settings,
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
        metadata: JSONPayload | None = None,
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
