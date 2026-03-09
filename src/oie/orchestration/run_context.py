from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict
from uuid import uuid4


@dataclass
class RunContext:
    run_id: str
    run_date: str
    mode: str
    config: Dict[str, Any] = field(default_factory=dict)
    flags: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    budgets: Dict[str, Any] = field(default_factory=dict)
    provider_events: list[Dict[str, Any]] = field(default_factory=list)
    provider_state: Dict[str, Any] = field(default_factory=dict)
    paths: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        config: Dict[str, Any] | None = None,
        flags: Dict[str, Any] | None = None,
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

        return cls(
            run_id=run_id,
            run_date=run_date,
            mode=resolved_mode,
            config=config,
            flags=flags,
            paths={
                "db_path": db_path,
            },
        )

    def add_provider_event(
        self,
        provider: str,
        event_type: str,
        message: str,
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        self.provider_events.append(
            {
                "provider": provider,
                "event_type": event_type,
                "message": message,
                "metadata": metadata or {},
            }
        )
