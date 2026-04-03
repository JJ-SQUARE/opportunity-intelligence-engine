from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class CollectorContributionExportService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def _get_output_dir(self) -> Path:
        output_dir_value = self.ctx.paths.get("output_dir")
        if not output_dir_value:
            base_output = ((self.ctx.config or {}).get("outputs", {}) or {}).get("path") or "data/outputs"
            run_id = self.ctx.run_id or "manual_run"
            output_dir_value = str(Path(base_output) / run_id)
            self.ctx.paths["output_dir"] = output_dir_value

        output_dir = Path(output_dir_value)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def export_csv(self, rows: List[Dict[str, Any]]) -> str:
        output_dir = self._get_output_dir()
        path = output_dir / "collector_contribution_metrics.csv"
        fieldnames = list(rows[0].keys()) if rows else []

        with path.open("w", encoding="utf-8", newline="") as fh:
            if fieldnames:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            else:
                fh.write("")

        self.ctx.paths["collector_contribution_metrics_csv"] = str(path)
        return str(path)

    def export_json(self, rows: List[Dict[str, Any]]) -> str:
        output_dir = self._get_output_dir()
        path = output_dir / "collector_contribution_metrics.json"
        path.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.ctx.paths["collector_contribution_metrics_json"] = str(path)
        return str(path)
