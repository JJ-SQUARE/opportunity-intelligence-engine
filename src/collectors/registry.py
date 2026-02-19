from __future__ import annotations
from typing import Any, Dict, List
from src.pipeline.job_contract import ensure_job_contract

Job = Dict[str, Any]

_COLLECTORS = {}

def register(collector):
    _COLLECTORS[collector.name] = collector
    return collector

def get_enabled_collectors(cfg: Dict[str, Any]) -> List[Any]:
    sources = (cfg.get("sources") or {})
    enabled = []
    for name, c in _COLLECTORS.items():
        c_cfg = sources.get(name, {})
        if c_cfg.get("enabled", False):
            enabled.append((c, c_cfg))
    return enabled

def run_collectors(cfg: Dict[str, Any]) -> List[Job]:
    jobs: List[Job] = []
    for collector, c_cfg in get_enabled_collectors(cfg):
        batch = collector.collect({**cfg, "collector_cfg": c_cfg})
        for j in batch:
            ensure_job_contract(j, source=collector.source, collector=collector.name)
        jobs.extend(batch)
    return jobs