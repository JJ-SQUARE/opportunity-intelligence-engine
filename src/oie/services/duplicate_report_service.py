from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class DuplicateReportService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.output_dir = Path(
            self.ctx.config.get("outputs", {}).get("path", "data/outputs")
        ) / self.ctx.run_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_suspected_duplicates_report(self, rows: List[Dict[str, Any]]) -> str:
        path = self.output_dir / "suspected_duplicates.csv"
        fieldnames = ["entity_type", "company", "primary_value", "reason", "run_id", "run_date"]

        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows([{field: row.get(field, "") for field in fieldnames} for row in rows])

        self.ctx.metrics["suspected_duplicates_report_written"] = len(rows)
        self.ctx.paths["suspected_duplicates_report"] = str(path)
        return str(path)
