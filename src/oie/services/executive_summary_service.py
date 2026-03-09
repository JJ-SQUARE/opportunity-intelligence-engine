from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class ExecutiveSummaryService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.output_dir = Path(
            self.ctx.config.get("outputs", {}).get("path", "data/outputs")
        ) / self.ctx.run_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build_summary(
        self,
        companies: List[Dict[str, Any]],
        leads: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        top_companies = sorted(
            companies,
            key=lambda x: x.get("opportunity_score", 0),
            reverse=True,
        )[:10]

        summary = {
            "run_id": self.ctx.run_id,
            "run_date": self.ctx.run_date,
            "mode": self.ctx.mode,
            "jobs_count": self.ctx.metrics.get("jobs_after_dedupe", 0),
            "companies_count": len(companies),
            "leads_count": len(leads),
            "companies_enriched": self.ctx.metrics.get("companies_enriched", 0),
            "duplicates_detected": self.ctx.metrics.get("suspected_duplicates_report_count", 0),
            "provider_events_count": len(self.ctx.provider_events),
            "top_companies": [
                {
                    "company_key": company.get("company_key"),
                    "company_display": company.get("company_display"),
                    "opportunity_score": company.get("opportunity_score"),
                    "company_type_ai": company.get("company_type_ai"),
                    "resolved_domain": company.get("resolved_domain"),
                }
                for company in top_companies
            ],
        }

        self.ctx.metrics["executive_summary_generated"] = True
        return summary

    def write_summary(self, summary: Dict[str, Any]) -> str:
        output_path = self.output_dir / "executive_summary.json"
        output_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.ctx.paths["executive_summary_json"] = str(output_path)
        return str(output_path)
