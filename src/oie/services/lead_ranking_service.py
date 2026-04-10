from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


TITLE_WEIGHTS = {
    "chief technology officer": 100,
    "cto": 100,
    "vp engineering": 90,
    "vice president engineering": 90,
    "head of engineering": 85,
    "director of engineering": 80,
    "engineering director": 80,
    "head of product": 70,
    "head of software": 70,
    "software director": 65,
    "product director": 60,
    "technical lead": 55,
    "engineering manager": 50,
    "software manager": 45,
}

NEGATIVE_TITLE_TERMS = {
    "compliance": -45,
    "operations": -35,
    "operating officer": -35,
    "human resources": -50,
    "hr": -50,
    "recruit": -60,
    "talent": -60,
    "people": -40,
    "finance": -35,
    "accounting": -35,
    "legal": -35,
    "marketing": -20,
    "sales": -20,
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
        if not value:
            return 0

        base_score = 0
        for known_title, score in TITLE_WEIGHTS.items():
            if known_title in value:
                base_score = max(base_score, score)

        if base_score == 0:
            if any(token in value for token in ("engineering", "technology", "product", "software", "developer")):
                base_score = 25
            elif any(token in value for token in ("director", "head", "vp", "chief")):
                base_score = 15
            else:
                base_score = 5

        penalty = 0
        for term, amount in NEGATIVE_TITLE_TERMS.items():
            if term in value:
                penalty += amount

        return max(0, base_score + penalty)

    def _source_score(self, source: str) -> int:
        return SOURCE_WEIGHTS.get((source or "").strip().lower(), 0)

    def _email_score(self, email: str) -> int:
        return 20 if (email or "").strip() else 0

    def _linkedin_score(self, linkedin_url: str) -> int:
        return 10 if (linkedin_url or "").strip() else 0

    def _email_quality_component(self, email_quality_score: Any) -> int:
        try:
            value = int(email_quality_score or 0)
        except Exception:
            value = 0
        value = max(0, min(value, 100))
        return value // 5

    def _confidence_component(self, lead_confidence: Any) -> int:
        try:
            value = float(lead_confidence or 0)
        except Exception:
            value = 0.0
        value = max(0.0, min(value, 1.0))
        return int(round(value * 20))

    def rank_leads(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ranked: List[Dict[str, Any]] = []

        for lead in leads:
            title_score = self._title_score(lead.get("contact_title", ""))
            source_score = self._source_score(lead.get("lead_source", ""))
            email_score = self._email_score(lead.get("email", ""))
            linkedin_score = self._linkedin_score(lead.get("linkedin_url", ""))
            email_quality_score = self._email_quality_component(lead.get("email_quality_score", 0))
            confidence_score = self._confidence_component(lead.get("lead_confidence", 0))

            lead_relevance_score = (
                title_score
                + source_score
                + email_score
                + linkedin_score
                + email_quality_score
                + confidence_score
            )

            enriched = dict(lead)
            enriched["lead_relevance_score"] = lead_relevance_score
            enriched["lead_score_title"] = title_score
            enriched["lead_score_source"] = source_score
            enriched["lead_score_email"] = email_score
            enriched["lead_score_linkedin"] = linkedin_score
            enriched["lead_score_email_quality"] = email_quality_score
            enriched["lead_score_confidence"] = confidence_score
            ranked.append(enriched)

        ranked.sort(
            key=lambda x: (
                int(x.get("lead_relevance_score", 0) or 0),
                self._title_score(x.get("contact_title", "")),
                self._email_quality_component(x.get("email_quality_score", 0)),
                self._confidence_component(x.get("lead_confidence", 0)),
                self._source_score(x.get("lead_source", "")),
                1 if (x.get("linkedin_url") or "").strip() else 0,
                (x.get("contact_name") or "").strip().lower(),
            ),
            reverse=True,
        )
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
                "email_quality_score": lead.get("email_quality_score", 0),
                "lead_capture_reason": lead.get("lead_capture_reason", ""),
                "lead_relevance_score": lead.get("lead_relevance_score", 0),
                "lead_score_title": lead.get("lead_score_title", 0),
                "lead_score_source": lead.get("lead_score_source", 0),
                "lead_score_email": lead.get("lead_score_email", 0),
                "lead_score_linkedin": lead.get("lead_score_linkedin", 0),
                "lead_score_email_quality": lead.get("lead_score_email_quality", 0),
                "lead_score_confidence": lead.get("lead_score_confidence", 0),
            }
            for lead in ranked[:limit]
        ]
