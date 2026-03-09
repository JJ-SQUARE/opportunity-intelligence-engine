from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, Sequence

import yaml

from oie.orchestration.pipeline_orchestrator import PipelineOrchestrator
from oie.orchestration.run_context import RunContext


def load_config(config_path: str | None) -> Dict[str, Any]:
    if not config_path:
        return {}

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    if not isinstance(data, dict):
        raise ValueError("Config file must contain a YAML object at root level")

    return data


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Opportunity Intelligence Engine pipeline runner")
    parser.add_argument("--config", dest="config_path", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-enrichment", action="store_true")
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--orchestrator-preview", action="store_true")
    parser.add_argument("--stage", default=None)
    parser.add_argument("--stop-after", default=None)
    parser.add_argument("--resume-from", default=None)
    return parser.parse_args(argv)


def build_runtime_flags(args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "dry_run": bool(args.dry_run),
        "no_enrichment": bool(args.no_enrichment),
        "no_llm": bool(args.no_llm),
        "cache_only": bool(args.cache_only),
        "orchestrator_preview": bool(args.orchestrator_preview),
        "config_path": args.config_path,
        "stage": args.stage,
        "stop_after": args.stop_after,
        "resume_from": args.resume_from,
    }


def run(cfg: Dict[str, Any]) -> Dict[str, Any]:
    flags = cfg.get("runtime_flags", {}) or {}
    ctx = RunContext.create(config=cfg, flags=flags)
    orchestrator = PipelineOrchestrator(ctx)

    if flags.get("orchestrator_preview", False):
        return orchestrator.run()

    # Lazy import para no arrastrar dependencias legacy durante tests de CLI
    from run_pipeline_legacy import run as legacy_run

    return legacy_run(cfg)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config(args.config_path)
    config["runtime_flags"] = build_runtime_flags(args)

    result = run(config)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
