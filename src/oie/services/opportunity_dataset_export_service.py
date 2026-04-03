from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

from oie.orchestration.run_context import RunContext


class OpportunityDatasetExportService:
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

    def _write_csv(self, filename: str, rows: List[Dict[str, object]]) -> str:
        output_dir = self._get_output_dir()
        output_path = output_dir / filename
        fieldnames = list(rows[0].keys()) if rows else []

        with output_path.open("w", encoding="utf-8", newline="") as fh:
            if fieldnames:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            else:
                fh.write("")

        return str(output_path)

    def export_dataset(self, dataset: List[Dict[str, object]]) -> str:
        path = self._write_csv("opportunities_export.csv", dataset)
        self.ctx.paths["opportunities_export"] = path
        return path

    def export_top_dataset(self, dataset: List[Dict[str, object]]) -> str:
        path = self._write_csv("top_opportunities_export.csv", dataset)
        self.ctx.paths["top_opportunities_export"] = path
        return path
