from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from oie.orchestration.run_context import RunContext


class RunMetricsSummaryExportService:
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

    def export_json(self, summary: Dict[str, Any]) -> str:
        output_dir = self._get_output_dir()
        out_path = output_dir / "run_metrics_summary.json"

        with out_path.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        self.ctx.paths["run_metrics_summary_json"] = str(out_path)
        return str(out_path)
