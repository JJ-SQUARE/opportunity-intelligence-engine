from __future__ import annotations

import argparse
import json
import os
from typing import Any, Sequence

import yaml

from oie.orchestration.run_context import RunContext
from oie.orchestration.pipeline_orchestrator import PipelineOrchestrator


def _expand_env_vars(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env_vars(v) for v in value]
    if isinstance(value, str):
        return os.path.expandvars(value)
    return value


def load_config(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return _expand_env_vars(raw)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/queries.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--stage", default=None)
    parser.add_argument("--stop-after", default=None)
    parser.add_argument("--resume-from", default=None)
    parser.add_argument("--orchestrator-preview", action="store_true")
    return parser.parse_args(argv)


def build_runtime_flags(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "dry_run": bool(getattr(args, "dry_run", False)),
        "cache_only": bool(getattr(args, "cache_only", False)),
        "no_llm": bool(getattr(args, "no_llm", False)),
        "config_path": getattr(args, "config", None),
        "stage": getattr(args, "stage", None),
        "stop_after": getattr(args, "stop_after", None),
        "resume_from": getattr(args, "resume_from", None),
        "orchestrator_preview": bool(getattr(args, "orchestrator_preview", False)),
    }


def run(config: dict[str, Any], flags: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = RunContext.create(config=config, flags=flags or {})
    orchestrator = PipelineOrchestrator(ctx)
    return orchestrator.run()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    flags = build_runtime_flags(args)

    result = run(config, flags=flags)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
