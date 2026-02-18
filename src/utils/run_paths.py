import os
from datetime import datetime
from typing import Dict, Any


def build_run_dir(cfg: Dict[str, Any]) -> str:
    runs_cfg = cfg.get("runs", {})
    enabled = bool(runs_cfg.get("enabled", True))

    base_dir = runs_cfg.get("base_dir", "runs")
    fmt = runs_cfg.get("run_id_format", "%Y-%m-%d_%H%M")

    if not enabled:
        # fallback legacy behavior
        return "data/processed"

    run_id = datetime.now().strftime(fmt)
    run_dir = os.path.join(base_dir, run_id)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def join_run_path(run_dir: str, filename: str) -> str:
    return os.path.join(run_dir, filename)