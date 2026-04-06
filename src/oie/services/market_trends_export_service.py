from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class MarketTrendsExportService:
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

    def _write_csv(self, filename: str, rows: List[Dict[str, Any]]) -> str:
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

    def _write_json(self, filename: str, payload: Dict[str, Any]) -> str:
        output_dir = self._get_output_dir()
        output_path = output_dir / filename
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(output_path)

    def export_source_trends(self, rows: List[Dict[str, Any]]) -> str:
        path = self._write_csv("market_trends_by_source.csv", rows)
        self.ctx.paths["market_trends_by_source_csv"] = path
        return path

    def export_country_trends(self, rows: List[Dict[str, Any]]) -> str:
        path = self._write_csv("market_trends_by_location.csv", rows)
        self.ctx.paths["market_trends_by_location_csv"] = path
        return path

    def export_new_companies_by_source(self, rows: List[Dict[str, Any]]) -> str:
        path = self._write_csv("market_new_companies_by_source.csv", rows)
        self.ctx.paths["market_new_companies_by_source_csv"] = path
        return path

    def export_summary_json(self, payload: Dict[str, Any]) -> str:
        path = self._write_json("market_trends_summary.json", payload)
        self.ctx.paths["market_trends_summary_json"] = path
        return path
