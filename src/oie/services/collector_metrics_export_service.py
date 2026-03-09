from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any

from oie.orchestration.run_context import RunContext


class CollectorMetricsExportService:

    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def export_json(self, metrics: List[Dict[str, Any]]) -> None:

        output_dir = Path(self.ctx.config["outputs"]["path"])
        output_dir.mkdir(parents=True, exist_ok=True)

        path = output_dir / "collector_coverage_metrics.json"

        with open(path, "w") as f:
            json.dump(metrics, f, indent=2)
