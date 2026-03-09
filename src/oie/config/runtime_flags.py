from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuntimeFlags:
    dry_run: bool = False
    no_enrichment: bool = False
    no_llm: bool = False
    cache_only: bool = False
    orchestrator_preview: bool = False
    config_path: str | None = None
    stage: str | None = None
    stop_after: str | None = None
    resume_from: str | None = None
