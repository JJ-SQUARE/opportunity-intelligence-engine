# src/collectors/registry.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple, Type

CollectorClass = Type[Any]
REGISTRY: Dict[str, CollectorClass] = {}


def register(cls: CollectorClass) -> CollectorClass:
    name = getattr(cls, "name", None)
    if not name:
        raise ValueError("Collector class missing 'name'")
    REGISTRY[name] = cls
    return cls


def _get_cfg_for_collector(cfg: Dict[str, Any], collector_name: str, collector_family: str) -> Dict[str, Any]:
    """
    Backwards compatible:
      1) Flat style: sources.<collector_name>
      2) Family nested: sources.<family>.<collector_name>
    """
    sources_cfg = (cfg.get("sources") or {})

    # 1) Flat style (current behavior)
    flat = sources_cfg.get(collector_name)
    if isinstance(flat, dict):
        return flat

    # 2) Family nested (new)
    fam = sources_cfg.get(collector_family)
    if isinstance(fam, dict):
        nested = fam.get(collector_name)
        if isinstance(nested, dict):
            return nested

    return {}


def get_enabled_collectors(cfg: Dict[str, Any]) -> List[Tuple[str, CollectorClass, Dict[str, Any]]]:
    enabled: List[Tuple[str, CollectorClass, Dict[str, Any]]] = []

    for name, cls in REGISTRY.items():
        family = (getattr(cls, "family", "unknown") or "unknown").strip()
        c_cfg = _get_cfg_for_collector(cfg, name, family)

        if bool((c_cfg or {}).get("enabled", False)):
            enabled.append((name, cls, c_cfg))

    return enabled