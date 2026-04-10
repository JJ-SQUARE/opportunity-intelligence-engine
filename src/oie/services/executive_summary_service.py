from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class ExecutiveSummaryService:
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

        ranked_leads = sorted(
            leads,
            key=lambda x: (
                x.get("lead_relevance_score", 0) or 0,
                x.get("email_quality_score", 0) or 0,
                x.get("lead_confidence", 0) or 0,
                x.get("lead_score_source", 0) or 0,
                1 if x.get("linkedin_url") else 0,
                x.get("contact_name", "") or "",
            ),
            reverse=True,
        )[:10]

        snapshot_counts = self.ctx.provider_state.get("run_metrics_summary_counts", {}) or {}
        effective_jobs_count = self.ctx.metrics.get(
            "jobs_after_company_limit",
            snapshot_counts.get("jobs_count", self.ctx.metrics.get("jobs_after_dedupe", 0)),
        )

        summary = {
            "run_id": self.ctx.run_id,
            "run_date": self.ctx.run_date,
            "mode": self.ctx.mode,
            "jobs_count": effective_jobs_count,
            "companies_count": snapshot_counts.get("companies_count", len(companies)),
            "leads_count": snapshot_counts.get("leads_count", len(leads)),
            "companies_enriched": self.ctx.metrics.get("companies_enriched", 0),
            "duplicates_detected": self.ctx.metrics.get("suspected_duplicates_report_count", 0),
            "provider_events_count": len(self.ctx.provider_events),
            "top_companies": [
                {
                    "company_key": company.get("company_key"),
                    "company_display": company.get("company_display"),
                    "opportunity_score": company.get("opportunity_score"),
                    "company_type_ai": company.get("company_type_ai"),
                    "classification_confidence_ai": company.get("classification_confidence_ai"),
                    "resolved_domain": company.get("resolved_domain"),
                    "score_breakdown": {
                        "score_openings": company.get("score_openings", 0),
                        "score_remote": company.get("score_remote", 0),
                        "score_contractor": company.get("score_contractor", 0),
                        "score_multi_source": company.get("score_multi_source", 0),
                        "score_company_type": company.get("score_company_type", 0),
                    },
                }
                for company in top_companies
            ],
            "top_leads": [
                {
                    "company_key": lead.get("company_key"),
                    "contact_name": lead.get("contact_name"),
                    "contact_title": lead.get("contact_title"),
                    "email": lead.get("email"),
                    "linkedin_url": lead.get("linkedin_url"),
                    "lead_source": lead.get("lead_source"),
                    "lead_confidence": lead.get("lead_confidence"),
                    "email_quality_score": lead.get("email_quality_score", 0),
                    "lead_capture_reason": lead.get("lead_capture_reason", ""),
                    "lead_relevance_score": lead.get("lead_relevance_score", 0),
                }
                for lead in ranked_leads
            ],
        }

        self.ctx.metrics["executive_summary_generated"] = True
        return summary

    def write_summary(self, summary: Dict[str, Any]) -> str:
        output_dir = self._get_output_dir()
        output_path = output_dir / "executive_summary.json"
        output_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.ctx.paths["executive_summary_json"] = str(output_path)
        return str(output_path)
