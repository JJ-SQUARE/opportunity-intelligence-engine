from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


TITLE_WEIGHTS = {
    "cto": 100,
    "vp engineering": 90,
    "head of engineering": 85,
    "engineering director": 80,
    "head of product": 70,
}


SOURCE_WEIGHTS = {
    "apollo_people": 30,
    "hunter_domain_search": 15,
    "stub_generation": 0,
}


class LeadRankingService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def _title_score(self, title: str) -> int:
        value = (title or "").strip().lower()
        for known_title, score in TITLE_WEIGHTS.items():
            if known_title in value:
                return score
        return 10 if value else 0

    def _source_score(self, source: str) -> int:
        return SOURCE_WEIGHTS.get((source or "").strip().lower(), 0)

    def _email_score(self, email: str) -> int:
        return 20 if (email or "").strip() else 0

    def _linkedin_score(self, linkedin_url: str) -> int:
        return 10 if (linkedin_url or "").strip() else 0

    def rank_leads(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ranked: List[Dict[str, Any]] = []

        for lead in leads:
            title_score = self._title_score(lead.get("contact_title", ""))
            source_score = self._source_score(lead.get("lead_source", ""))
            email_score = self._email_score(lead.get("email", ""))
            linkedin_score = self._linkedin_score(lead.get("linkedin_url", ""))

            lead_relevance_score = title_score + source_score + email_score + linkedin_score

            enriched = dict(lead)
            enriched["lead_relevance_score"] = lead_relevance_score
            enriched["lead_score_title"] = title_score
            enriched["lead_score_source"] = source_score
            enriched["lead_score_email"] = email_score
            enriched["lead_score_linkedin"] = linkedin_score
            ranked.append(enriched)

        ranked.sort(key=lambda x: x.get("lead_relevance_score", 0), reverse=True)
        self.ctx.metrics["leads_ranked"] = len(ranked)
        return ranked

    def select_best_lead_per_company(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        best_by_company: Dict[str, Dict[str, Any]] = {}

        for lead in self.rank_leads(leads):
            company_key = lead.get("company_key") or ""
            if not company_key:
                continue

            if company_key not in best_by_company:
                best_by_company[company_key] = lead

        selected = list(best_by_company.values())
        self.ctx.metrics["best_leads_selected"] = len(selected)
        return selected

    def build_top_leads(self, leads: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
        ranked = self.rank_leads(leads)

        return [
            {
                "company_key": lead.get("company_key"),
                "contact_name": lead.get("contact_name"),
                "contact_title": lead.get("contact_title"),
                "email": lead.get("email"),
                "linkedin_url": lead.get("linkedin_url"),
                "lead_source": lead.get("lead_source"),
                "lead_confidence": lead.get("lead_confidence"),
                "lead_relevance_score": lead.get("lead_relevance_score", 0),
                "lead_score_title": lead.get("lead_score_title", 0),
                "lead_score_source": lead.get("lead_score_source", 0),
                "lead_score_email": lead.get("lead_score_email", 0),
                "lead_score_linkedin": lead.get("lead_score_linkedin", 0),
            }
            for lead in ranked[:limit]
        ]
