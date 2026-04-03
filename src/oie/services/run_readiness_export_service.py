from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from oie.orchestration.run_context import RunContext


class RunReadinessExportService:
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

    def export_json(self, report: Dict[str, Any]) -> str:
        output_dir = self._get_output_dir()
        path = output_dir / "run_readiness_report.json"
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.ctx.paths["run_readiness_report_json"] = str(path)
        return str(path)
