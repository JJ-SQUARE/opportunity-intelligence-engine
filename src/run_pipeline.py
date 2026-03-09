from __future__ import annotations

from typing import Any, Dict

from orchestration.pipeline_orchestrator import PipelineOrchestrator
from orchestration.run_context import RunContext

from run_pipeline_legacy import run as legacy_run


def run(cfg: Dict[str, Any]) -> Dict[str, Any]:
    flags = cfg.get("runtime_flags", {}) or {}
    ctx = RunContext.create(config=cfg, flags=flags)
    orchestrator = PipelineOrchestrator(ctx)

    # Modo temporal para probar la nueva arquitectura
    if flags.get("orchestrator_preview", False):
        return orchestrator.run()

    # Flujo actual intacto mientras migramos etapa por etapa
    return legacy_run(cfg)