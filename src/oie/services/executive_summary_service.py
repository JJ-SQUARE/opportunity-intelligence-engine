from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.services.commercial_row_service import CommercialRowService


class ExecutiveSummaryService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.commercial_row_service = CommercialRowService(ctx)
        self.commercial_signal_service = self.commercial_row_service.commercial_signal_service
        self.commercial_selection_service = self.commercial_row_service.commercial_selection_service

    def _get_output_dir(self) -> Path:
        output_dir_value = self.ctx.paths.get("output_dir")

        if not output_dir_value:
            base_output = ((self.ctx.config or {}).get("outputs", {}) or {}).get("path") or "data/outputs"
            output_dir_value = str(Path(base_output) / self.ctx.run_id)
            self.ctx.paths["output_dir"] = output_dir_value

        output_dir = Path(output_dir_value)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _serialize_company(self, company: Dict[str, Any]) -> Dict[str, Any]:
        finalized = dict(company)

        # Fallback: si no viene finalizado desde CommercialRowService
        if "icp_bucket" not in finalized or "reachability_ready" not in finalized:
            finalized = self.commercial_signal_service.finalize_row(finalized)

        return {
            "company_key": finalized.get("company_key"),
            "company_display": finalized.get("company_display"),
            "opportunity_score": finalized.get("opportunity_score"),
            "company_type_ai": finalized.get("company_type_ai"),
            "classification_confidence_ai": finalized.get("classification_confidence_ai"),
            "resolved_domain": finalized.get("resolved_domain"),
            "domain_validation_status": finalized.get("domain_validation_status"),
            "linkedin_company_url": finalized.get("linkedin_company_url"),
            "suggested_outreach_channel": finalized.get("suggested_outreach_channel"),
            "outreach_status": finalized.get("outreach_status"),
            "commercial_bucket": finalized.get("commercial_bucket"),
            "commercial_priority_score": finalized.get("commercial_priority_score"),
            "reachability_ready": bool(
                int(
                    finalized.get(
                        "soft_reachability_ready",
                        finalized.get("reachability_ready", 0),
                    )
                    or 0
                )
            ),
            "icp_bucket": finalized.get("icp_bucket"),
            "score_breakdown": {
                "score_openings": finalized.get("score_openings", 0),
                "score_remote": finalized.get("score_remote", 0),
                "score_contractor": finalized.get("score_contractor", 0),
                "score_multi_source": finalized.get("score_multi_source", 0),
                "score_company_type": finalized.get("score_company_type", 0),
            },
        }

    def build_summary(
        self,
        companies: List[Dict[str, Any]],
        leads: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        top_companies = self.commercial_selection_service.top_companies(companies, limit=10, include_non_actionable_fallback=True)
        top_leads = self.commercial_selection_service.top_leads(leads, limit=10)

        reachability_ready = 0
        strong_icp = 0
        strong_icp_reachable = 0

        for c in companies:
            f = dict(c)

            # Fallback igual que arriba
            if "icp_bucket" not in f or "reachability_ready" not in f:
                f = self.commercial_signal_service.finalize_row(f)
            is_reachable = bool(
                int(
                    f.get(
                        "soft_reachability_ready",
                        f.get("reachability_ready", 0),
                    )
                    or 0
                )
            )
            is_strong = f.get("icp_bucket") == "strong_icp"

            if is_reachable:
                reachability_ready += 1
            if is_strong:
                strong_icp += 1
                if is_reachable:
                    strong_icp_reachable += 1

        summary = {
            "run_id": self.ctx.run_id,
            "run_date": self.ctx.run_date,
            "mode": self.ctx.mode,
            "companies_count": len(companies),
            "leads_count": len(leads),
            "top_companies": [self._serialize_company(c) for c in top_companies],
            "top_leads": [
                {
                    "company_key": l.get("company_key"),
                    "contact_name": l.get("contact_name"),
                    "contact_title": l.get("contact_title"),
                    "email": l.get("email"),
                    "linkedin_url": l.get("linkedin_url"),
                    "lead_source": l.get("lead_source"),
                    "lead_confidence": l.get("lead_confidence"),
                    "email_quality_score": l.get("email_quality_score", 0),
                    "lead_capture_reason": l.get("lead_capture_reason", ""),
                    "lead_relevance_score": l.get("lead_relevance_score", 0),
                }
                for l in top_leads
            ],
            "icp_summary": {
                "strong_icp_companies": strong_icp,
                "strong_icp_with_reachability": strong_icp_reachable,
                "reachability_ready_companies": reachability_ready,
            },
        }

        self.ctx.metrics["executive_summary_generated"] = True
        return summary

    def write_summary(self, summary: Dict[str, Any]) -> str:
        output_dir = self._get_output_dir()
        output_path = output_dir / "executive_summary.json"

        output_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        self.ctx.paths["executive_summary_json"] = str(output_path)
        return str(output_path)
