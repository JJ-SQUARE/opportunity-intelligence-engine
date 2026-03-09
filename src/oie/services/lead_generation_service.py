from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class LeadGenerationService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def generate_leads(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self.ctx.flags.get("no_enrichment"):
            self.ctx.metrics["lead_generation_skipped_no_enrichment"] = True
            return []

        leads: List[Dict[str, Any]] = []

        for company in companies:
            company_key = company.get("company_key")
            company_display = company.get("company_display") or company.get("company") or ""
            resolved_domain = company.get("resolved_domain") or ""

            if not company_key:
                continue

            email = ""
            linkedin_url = ""

            if resolved_domain:
                safe_name = company_display.strip().lower().replace(" ", ".")
                email = f"engineering@{resolved_domain}"
                linkedin_url = f"https://www.linkedin.com/company/{resolved_domain.split('.')[0]}"

            leads.append(
                {
                    "company_key": company_key,
                    "contact_name": "",
                    "contact_title": "Engineering Leadership",
                    "email": email,
                    "linkedin_url": linkedin_url,
                    "lead_source": "stub_generation",
                    "lead_confidence": 0.2,
                }
            )

        self.ctx.metrics["leads_generated"] = len(leads)
        return leads
