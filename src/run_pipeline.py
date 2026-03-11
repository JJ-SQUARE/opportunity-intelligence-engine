from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import yaml

from oie.orchestration.pipeline_orchestrator import PipelineOrchestrator
from oie.orchestration.run_context import RunContext


def load_yaml_config(path: str | None) -> Dict[str, Any]:
    if not path:
        return {}

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    if not isinstance(data, dict):
        raise ValueError("YAML config must load into a dictionary.")
    return data



def load_config(path: str | None) -> Dict[str, Any]:
    return load_yaml_config(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Opportunity Intelligence Engine pipeline runner")
    parser.add_argument("--config", dest="config_path", default=None, help="Path to YAML config file")
    parser.add_argument("--dry-run", action="store_true", help="Skip provider-backed executions")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM-backed classification/enrichment steps")
    parser.add_argument("--cache-only", action="store_true", help="Only use cache, skip external provider execution")
    parser.add_argument("--orchestrator-preview", action="store_true", help="Reserved compatibility flag")
    parser.add_argument("--stage", default=None)
    parser.add_argument("--stop-after", default=None)
    parser.add_argument("--resume-from", default=None)
    return parser.parse_args(argv)


def build_runtime_flags(args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "dry_run": bool(args.dry_run),
        "no_enrichment": False,
        "no_llm": bool(args.no_llm),
        "cache_only": bool(args.cache_only),
        "orchestrator_preview": bool(args.orchestrator_preview),
        "config_path": args.config_path,
        "stage": args.stage,
        "stop_after": args.stop_after,
        "resume_from": args.resume_from,
    }


def run(config: Dict[str, Any], flags: Dict[str, Any] | None = None) -> Dict[str, Any]:
    ctx = RunContext.create(config=config, flags=flags or {})
    orchestrator = PipelineOrchestrator(ctx)
    return orchestrator.run()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    flags = build_runtime_flags(args)
    config = load_yaml_config(args.config_path)

    result = run(config, flags=flags)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
