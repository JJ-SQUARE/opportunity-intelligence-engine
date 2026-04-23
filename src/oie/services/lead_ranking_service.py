from __future__ import annotations

from typing import Any, Dict, List, Optional
from oie.services.commercial_selection_service import CommercialSelectionService

from oie.orchestration.run_context import RunContext
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import ProviderExecutionService


TITLE_WEIGHTS = {
    "chief technology officer": 100,
    "cto": 100,
    "chief information officer": 95,
    "cio": 95,
    "chief digital officer": 92,
    "cdo": 92,
    "chief operating officer": 70,
    "coo": 70,
    "chief product officer": 68,
    "cpo": 68,
    "vp engineering": 90,
    "vice president engineering": 90,
    "vp of engineering": 90,
    "vp technology": 82,
    "vp digital": 72,
    "director of engineering": 80,
    "engineering director": 80,
    "director of technology": 76,
    "director of software engineering": 82,
    "director of platform engineering": 78,
    "head of engineering": 85,
    "head of technology": 80,
    "head of software engineering": 82,
    "head of platform engineering": 78,
    "head of data engineering": 72,
    "head of digital": 70,
    "head of software": 72,
    "head of product": 48,
    "engineering manager": 62,
    "platform engineering manager": 64,
    "software engineering manager": 64,
    "data engineering manager": 58,
    "it manager": 54,
    "innovation manager": 42,
    "digital channels manager": 38,
    "software manager": 48,
    "software director": 65,
    "product director": 42,
    "technical lead": 40,
    "solutions architect": 36,
    "enterprise architect": 34,
    "ceo": 10,
    "chief executive officer": 10,
    "director": 12,
}

NEGATIVE_TITLE_TERMS = {
    "compliance": -55,
    "operations": -50,
    "operating officer": -50,
    "human resources": -60,
    "hr": -60,
    "recruit": -70,
    "talent": -70,
    "people": -55,
    "finance": -45,
    "accounting": -45,
    "legal": -45,
    "marketing": -30,
    "sales": -30,
    "customer success": -35,
    "support": -30,
    "product": -18,
    "procurement": -40,
    "purchasing": -40,
    "buyer": -40,
    "business development": -35,
    "partnerships": -25,
}

GENERIC_EXACT_TITLE_SCORES = {
    "chief": 30,
    "vp": 25,
    "vice president": 25,
    "head": 22,
    "director": 18,
    "manager": 12,
    "lead": 10,
}

SOURCE_WEIGHTS = {
    "apollo_people": 30,
    "hunter_domain_search": 15,
    "stub_generation": 0,
}

DEPRIORITIZED_COMPANY_TYPES = {
    "competitor",
    "staffing",
    "consulting",
    "marketplace",
    "job_board",
}

COMPANY_TYPE_ALIASES = {
    "staffing_agency": "staffing",
    "outsourcing": "consulting",
}


class LeadRankingService:
    def __init__(
        self,
        ctx: RunContext,
        provider_control_service: Optional[ProviderControlService] = None,
    ) -> None:
        self.ctx = ctx
        self.provider_control_service = provider_control_service
        self.commercial_selection_service = CommercialSelectionService()

        if provider_control_service:
            self.provider_execution_service = ProviderExecutionService(ctx, provider_control_service)
        else:
            self.provider_execution_service = None

    def _normalized_title(self, title: str) -> str:
        return " ".join((title or "").strip().lower().replace("/", " ").replace("-", " ").split())

    def _title_score(self, title: str) -> int:
        value = self._normalized_title(title)
        if not value:
            return 0

        exact_generic_score = GENERIC_EXACT_TITLE_SCORES.get(value)
        if exact_generic_score is not None:
            return exact_generic_score

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

    def _contact_completeness_penalty(self, email: str, linkedin_url: str) -> int:
        has_email = bool((email or "").strip())
        has_linkedin = bool((linkedin_url or "").strip())

        if has_email:
            return 0
        if has_linkedin:
            return -15
        return -35

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

    def _normalized_company_type(self, value: Any) -> str:
        normalized = str(value or "").strip().lower()
        return COMPANY_TYPE_ALIASES.get(normalized, normalized)

    def _company_penalty_component(self, lead: Dict[str, Any]) -> int:
        company_type = self._normalized_company_type(lead.get("company_type_ai") or "")
        if company_type in DEPRIORITIZED_COMPANY_TYPES:
            return -80

        try:
            competitor_penalty = float(lead.get("score_penalty_competitor") or 0)
        except Exception:
            competitor_penalty = 0.0

        if competitor_penalty <= -20:
            return -70

        return 0


    def _build_lead_scoring_context(self) -> Dict[str, Any]:
        return {
            "target_buyer_personas": [
                "cto",
                "cio",
                "cdo",
                "vp engineering",
                "vp technology",
                "director of engineering",
                "engineering director",
                "director of software engineering",
                "director of platform engineering",
                "head of engineering",
                "head of technology",
                "head of software engineering",
                "head of platform engineering",
                "engineering manager",
                "software engineering manager",
                "platform engineering manager",
                "it manager",
            ],
            "priority_industries": [
                "banking and financial services",
                "bfsi",
                "insurance",
                "aerospace",
                "airlines",
                "technology",
                "healthcare",
                "life sciences",
                "logistics",
                "transportation",
            ],
            "priority_regions": [
                "mexico",
                "panama",
                "colombia",
                "chile",
                "ecuador",
                "argentina",
                "uruguay",
                "peru",
                "guatemala",
                "el salvador",
                "costa rica",
                "republica dominicana",
                "dominican republic",
                "bolivia",
                "paraguay",
            ],
            "commercial_rules": {
                "company_fit_more_important_than_vacancy_volume": True,
                "pain_and_buying_probability_are_both_crucial": True,
                "decision_maker_seniority_required_for_top_scores": True,
                "competitors_should_be_preserved_but_penalized": True,
                "multiple_relevant_contacts_per_company_are_valuable": True,
            },
        }

    def _normalize_lead_label(self, score: int, label: str | None) -> str:
        value = (label or "").strip().lower()
        if value in {"high", "medium", "low"}:
            return value
        if score >= 75:
            return "high"
        if score >= 45:
            return "medium"
        return "low"

    def _looks_ranked(self, lead: Dict[str, Any]) -> bool:
        if not isinstance(lead, dict):
            return False

        if "lead_relevance_score" not in lead:
            return False

        ranking_markers = (
            "lead_score_title",
            "lead_score_source",
            "lead_score_email",
            "lead_score_linkedin",
            "lead_score_email_quality",
            "lead_score_confidence",
            "lead_score_completeness_penalty",
            "lead_score_company_penalty",
            "lead_priority_label",
            "lead_scoring_provider",
            "lead_scoring_mode",
        )
        return any(marker in lead for marker in ranking_markers)

    def _ensure_ranked(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if leads and all(self._looks_ranked(lead) for lead in leads):
            return list(leads)
        return self.rank_leads(leads)

    def _score_lead_with_llm(self, lead: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.provider_control_service or not self.provider_execution_service:
            return None

        if self.ctx.flags.get("no_llm"):
            return None

        client = self.provider_control_service.registry.get_client("openai")
        if client is None:
            return None

        score_fn = getattr(client, "score_lead", None)
        if not callable(score_fn):
            return None

        try:
            payload = dict(lead)
            payload["lead_scoring_context"] = self._build_lead_scoring_context()

            result = self.provider_execution_service.execute(
                "openai",
                "score_lead",
                score_fn,
                payload,
                cost=1,
            )
            if not result or not isinstance(result, dict):
                return None

            lead_score = result.get("lead_relevance_score")
            if lead_score is None:
                return None

            score_int = max(0, min(int(lead_score), 100))

            return {
                "lead_relevance_score": score_int,
                "lead_priority_label": self._normalize_lead_label(
                    score_int,
                    result.get("lead_priority_label"),
                ),
                "lead_decision_maker_score": int(result.get("lead_decision_maker_score", 0) or 0),
                "lead_icp_fit_score": int(result.get("lead_icp_fit_score", 0) or 0),
                "lead_contact_completeness_score": int(result.get("lead_contact_completeness_score", 0) or 0),
                "lead_penalty_negative_title": int(result.get("lead_penalty_negative_title", 0) or 0),
                "lead_score_reason": str(result.get("lead_score_reason") or "").strip(),
                "lead_scoring_provider": str(result.get("lead_scoring_provider") or "openai").strip().lower(),
                "lead_scoring_model": str(result.get("lead_scoring_model") or "").strip(),
                "lead_scoring_mode": str(result.get("lead_scoring_mode") or "llm").strip().lower(),
            }
        except Exception:
            return None

    def rank_leads(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ranked: List[Dict[str, Any]] = []
        llm_used = 0
        rules_used = 0

        for lead in leads:
            title_score = self._title_score(lead.get("contact_title", ""))
            source_score = self._source_score(lead.get("lead_source", ""))
            email_score = self._email_score(lead.get("email", ""))
            linkedin_score = self._linkedin_score(lead.get("linkedin_url", ""))
            email_quality_score = self._email_quality_component(lead.get("email_quality_score", 0))
            confidence_score = self._confidence_component(lead.get("lead_confidence", 0))
            completeness_penalty = self._contact_completeness_penalty(
                lead.get("email", ""),
                lead.get("linkedin_url", ""),
            )
            company_penalty = self._company_penalty_component(lead)

            lead_relevance_score = (
                title_score
                + source_score
                + email_score
                + linkedin_score
                + email_quality_score
                + confidence_score
                + completeness_penalty
                + company_penalty
            )

            enriched = dict(lead)
            enriched["lead_relevance_score"] = lead_relevance_score
            enriched["lead_score_title"] = title_score
            enriched["lead_score_source"] = source_score
            enriched["lead_score_email"] = email_score
            enriched["lead_score_linkedin"] = linkedin_score
            enriched["lead_score_email_quality"] = email_quality_score
            enriched["lead_score_confidence"] = confidence_score
            enriched["lead_score_completeness_penalty"] = completeness_penalty
            enriched["lead_score_company_penalty"] = company_penalty
            enriched["lead_priority_label"] = self._normalize_lead_label(lead_relevance_score, None)
            enriched["lead_score_reason"] = ""
            enriched["lead_scoring_provider"] = "rules"
            enriched["lead_scoring_model"] = ""
            enriched["lead_scoring_mode"] = "fallback_rules"

            llm_result = self._score_lead_with_llm(enriched)
            if llm_result:
                enriched.update(llm_result)
                llm_used += 1
            else:
                rules_used += 1

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
        self.ctx.metrics["lead_scoring_llm_used"] = llm_used
        self.ctx.metrics["lead_scoring_rules_used"] = rules_used
        return ranked

    def select_best_lead_per_company(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self.select_top_leads_per_company(leads, max_leads_per_company=1)

    def select_top_leads_per_company(
        self,
        leads: List[Dict[str, Any]],
        max_leads_per_company: int = 3,
    ) -> List[Dict[str, Any]]:
        ranked = self._ensure_ranked(leads)
        selected = self.commercial_selection_service.select_top_leads_per_company(
            ranked,
            max_leads_per_company=max_leads_per_company,
            min_relevance_score=45,
            require_channel=True,
        )

        self.ctx.metrics["best_leads_selected"] = len(selected)
        self.ctx.metrics["best_leads_selected_companies"] = len(
            {str(lead.get("company_key") or "").strip() for lead in selected if str(lead.get("company_key") or "").strip()}
        )
        self.ctx.metrics["best_leads_selected_max_per_company"] = max(1, int(max_leads_per_company or 1))
        return selected

    def build_top_leads(self, leads: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
        ranked = self._ensure_ranked(leads)

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
                "lead_score_completeness_penalty": lead.get("lead_score_completeness_penalty", 0),
                "lead_score_company_penalty": lead.get("lead_score_company_penalty", 0),
                "lead_priority_label": lead.get("lead_priority_label", ""),
                "lead_score_reason": lead.get("lead_score_reason", ""),
                "lead_scoring_provider": lead.get("lead_scoring_provider", ""),
                "lead_scoring_model": lead.get("lead_scoring_model", ""),
                "lead_scoring_mode": lead.get("lead_scoring_mode", ""),
            }
            for lead in ranked[:limit]
        ]
