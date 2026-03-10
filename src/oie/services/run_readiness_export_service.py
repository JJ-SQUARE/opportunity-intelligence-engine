from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from oie.orchestration.run_context import RunContext


class RunReadinessExportService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.output_dir = Path(
            self.ctx.config.get("outputs", {}).get("path", "data/outputs")
        ) / self.ctx.run_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_json(self, report: Dict[str, Any]) -> str:
        path = self.output_dir / "run_readiness_report.json"
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.ctx.paths["run_readiness_report_json"] = str(path)
        return str(path)
