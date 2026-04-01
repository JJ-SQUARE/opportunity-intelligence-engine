from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class ProviderOperationMetricsExportService:
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
        out_path = output_dir / "provider_operation_metrics.csv"

        fieldnames = [
            "provider",
            "operation",
            "max_calls",
            "used_calls",
            "remaining_calls",
            "started",
            "success",
            "retry_count",
            "blocked_budget",
            "errors_timeout",
            "errors_execution_error",
        ]

        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        self.ctx.paths["provider_operation_metrics_csv"] = str(out_path)
        return str(out_path)

    def export_json(self, rows: List[Dict[str, Any]]) -> str:
        output_dir = self._get_output_dir()
        out_path = output_dir / "provider_operation_metrics.json"

        with out_path.open("w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)

        self.ctx.paths["provider_operation_metrics_json"] = str(out_path)
        return str(out_path)
