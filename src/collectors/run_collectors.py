from typing import Any, Dict, List

from collectors.registry import REGISTRY
from collectors.base import BaseCollector

def _is_enabled(cfg: Dict[str, Any], path: List[str]) -> bool:
    cur = cfg
    for k in path:
        cur = (cur or {}).get(k, {})
    return bool((cur or {}).get("enabled", False))

def run_collectors(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    sources = cfg.get("sources", {})
    out: List[Dict[str, Any]] = []

    for name, cls in REGISTRY.items():
        collector: BaseCollector = cls()

        # convención: el collector declara su family y usamos eso para leer cfg
        family = getattr(collector, "family", "unknown")
        enabled = _is_enabled(cfg, ["sources", family, name]) if family != "unknown" else False

        if not enabled:
            continue

        batch = collector.fetch(cfg)
        out.extend(batch)

    return out