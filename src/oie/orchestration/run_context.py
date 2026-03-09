from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict


@dataclass
class RunContext:
    run_id: str
    run_date: str
    config: Dict[str, Any]
    flags: Dict[str, Any] = field(default_factory=dict)
    budgets: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    provider_state: Dict[str, Any] = field(default_factory=dict)
    paths: Dict[str, str] = field(default_factory=dict)
    mode: str = "normal"

    @classmethod
    def create(cls, config: Dict[str, Any], flags: Dict[str, Any] | None = None) -> "RunContext":
        now = datetime.now(UTC)
        run_id = now.strftime("%Y%m%d_%H%M%S")
        flags = flags or {}

        mode = "normal"
        if flags.get("dry_run"):
            mode = "dry-run"
        elif flags.get("cache_only"):
            mode = "cache-only"

        paths = {
            "db_path": config.get("database", {}).get("path", "data/oie.db"),
        }

        return cls(
            run_id=run_id,
            run_date=now.isoformat(),
            config=config,
            flags=flags,
            paths=paths,
            mode=mode,
        )
