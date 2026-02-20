# src/collectors/run_collectors.py
from __future__ import annotations

from typing import Any, Dict, List

from collectors.autodiscover import autodiscover_collectors
from collectors.registry import get_enabled_collectors
from pipeline.job_contract import ensure_job_contract

Job = Dict[str, Any]


def run_collectors(cfg: Dict[str, Any]) -> List[Job]:
    # IMPORTANT: load modules so @register executes
    autodiscover_collectors()

    out: List[Job] = []

    enabled = get_enabled_collectors(cfg)
    print(f"[collectors] enabled={len(enabled)} -> {[k for (k, _, __) in enabled]}")

    for registry_key, cls, c_cfg in enabled:
        collector = cls()
        collector_name = getattr(collector, "name", registry_key)
        collector_source = getattr(collector, "source", registry_key)
        collector_family = getattr(collector, "family", None)

        print(
            f"[collectors] running '{collector_name}' "
            f"source='{collector_source}' family='{collector_family}' "
            f"cfg_keys={list((c_cfg or {}).keys())}"
        )

        try:
            batch = collector.collect({**cfg, "collector_cfg": c_cfg}) or []
        except Exception as e:
            print(f"[collectors][ERROR] collector='{collector_name}' -> {type(e).__name__}: {e}")
            continue

        print(f"[collectors] collector='{collector_name}' returned {len(batch)} jobs")

        for j in batch:
            ensure_job_contract(j, source=collector_source, collector=collector_name)

        out.extend(batch)

    print(f"[collectors] total_jobs={len(out)}")
    return out