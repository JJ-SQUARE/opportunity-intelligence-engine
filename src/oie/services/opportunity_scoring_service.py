from __future__ import annotations

from typing import Any, Dict, List, Optional

from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import ProviderExecutionService

from oie.orchestration.run_context import RunContext


CLASSIFICATION_WEIGHTS = {
    "end_client": 20,
    "consulting": 10,
    "staffing": 5,
    "marketplace": 0,
    "job_board": -10,
    "unknown": 0,
    "": 0,
}

CLASSIFICATION_ALIASES = {
    "product_company": "end_client",
    "staffing_agency": "staffing",
}


class OpportunityScoringService:
    def __init__(
        self,
        ctx: RunContext,
        provider_control_service: Optional[ProviderControlService] = None,
    ) -> None:
        self.ctx = ctx
        self.provider_control_service = provider_control_service

        if provider_control_service:
            self.provider_execution_service = ProviderExecutionService(ctx, provider_control_service)
        else:
            self.provider_execution_service = None

    def _normalized_company_type(self, company_type: str) -> str:
        value = (company_type or "").strip().lower()
        return CLASSIFICATION_ALIASES.get(value, value)
    def _build_scoring_context(self) -> Dict[str, Any]:
        return {
            "target_buyer_personas": [
                "cto",
                "coo",
                "cdo",
                "vp engineering",
                "engineering director",
                "engineering manager",
                "it manager",
                "innovation manager",
                "digital channels manager",
            ],
            "priority_industries": [
                "banking and financial services",
                "banking",
                "financial services",
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
                "united states of america",
                "canada",
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
                "small_companies_outside_icp_should_be_penalized": True,
            },
            "service_lines": {
                "talent_as_a_service": "senior engineers and technical experts integrated quickly for staff augmentation needs",
                "agile_solution_delivery": "end-to-end product delivery and modernization through agile engineering cells",
                "managed_it_services": "operation, support, and maintenance of critical platforms",
            },
        }

    def _normalize_label(self, score: int, label: str | None) -> str:
        value = (label or "").strip().lower()

        if value in {"high", "medium", "low"}:
            return value

        if score >= 75:
            return "high"
        if score >= 45:
            return "medium"
        return "low"

    def _score_company_with_llm(self, company: Dict[str, Any]) -> Optional[Dict[str, Any]]:

        if not self.provider_control_service or not self.provider_execution_service:
            return None

        if self.ctx.flags.get("no_llm"):
            return None

        client = self.provider_control_service.registry.get_client("openai")
        if client is None:
            return None

        score_fn = getattr(client, "score_company", None)
        if not callable(score_fn):
            return None

        try:
            company_payload = dict(company)
            company_payload["scoring_context"] = self._build_scoring_context()

            result = self.provider_execution_service.execute(
                "openai",
                "score_company",
                score_fn,
                company_payload,
                cost=1,
            )
            if not result or not isinstance(result, dict):
                return None

            opportunity_score = result.get("opportunity_score")
            if opportunity_score is None:
                return None

            score_int = int(opportunity_score)

            enriched = {
                "opportunity_score": score_int,
                "opportunity_label": self._normalize_label(
                    score_int,
                    result.get("opportunity_label"),
                ),
                "score_icp_fit": int(result.get("score_icp_fit", 0) or 0),
                "score_pain_urgency": int(result.get("score_pain_urgency", 0) or 0),
                "score_region_fit": int(result.get("score_region_fit", 0) or 0),
                "score_company_scale": int(result.get("score_company_scale", 0) or 0),
                "score_role_seniority_mix": int(result.get("score_role_seniority_mix", 0) or 0),
                "score_penalty_competitor": int(result.get("score_penalty_competitor", 0) or 0),
                "score_penalty_negative_signals": int(result.get("score_penalty_negative_signals", 0) or 0),
                "primary_service_fit": str(result.get("primary_service_fit") or "unknown").strip().lower(),
                "buyer_persona_fit": str(result.get("buyer_persona_fit") or "low").strip().lower(),
                "opportunity_score_reason": str(result.get("opportunity_score_reason") or "").strip(),
                "scoring_provider": str(result.get("scoring_provider") or "openai").strip().lower(),
                "scoring_model": str(result.get("scoring_model") or "").strip(),
                "scoring_mode": str(result.get("scoring_mode") or "llm").strip().lower(),
            }

            enriched["opportunity_score"] = max(0, min(enriched["opportunity_score"], 100))
            return enriched

        except Exception:
            return None

    def _score_company(self, company: Dict[str, Any]) -> Dict[str, Any]:
        total_openings = int(company.get("total_openings", 0) or 0)
        remote_jobs = int(company.get("remote_jobs", 0) or 0)
        contractor_jobs = int(company.get("contractor_jobs", 0) or 0)
        multi_source_signal = bool(company.get("multi_source_signal", False))
        company_type = self._normalized_company_type(company.get("company_type_ai") or "")

        score_openings = min(total_openings * 8, 40)
        score_remote = min(remote_jobs * 4, 20)
        score_contractor = min(contractor_jobs * 6, 20)
        score_multi_source = 10 if multi_source_signal else 0
        score_company_type = CLASSIFICATION_WEIGHTS.get(company_type, 0)

        total_score = (
            score_openings
            + score_remote
            + score_contractor
            + score_multi_source
            + score_company_type
        )

        label = "high" if total_score >= 75 else "medium" if total_score >= 45 else "low"

        return {
            "score_openings": score_openings,
            "score_remote": score_remote,
            "score_contractor": score_contractor,
            "score_multi_source": score_multi_source,
            "score_company_type": score_company_type,
            "opportunity_score": total_score,
            "opportunity_label": label,
            "primary_service_fit": "unknown",
            "buyer_persona_fit": "low",
            "opportunity_score_reason": "",
            "scoring_provider": "rules",
            "scoring_model": "",
            "scoring_mode": "fallback_rules",
        }

    def score_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        scored: List[Dict[str, Any]] = []

        llm_used = 0
        rules_used = 0

        for company in companies:
            llm_score = self._score_company_with_llm(company)

            enriched = dict(company)

            if llm_score:
                enriched.update(llm_score)
                llm_used += 1
            else:
                score_components = self._score_company(company)
                enriched.update(score_components)
                rules_used += 1

            scored.append(enriched)

        scored.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)

        self.ctx.metrics["companies_scored"] = len(scored)
        self.ctx.metrics["scoring_completed"] = True
        self.ctx.metrics["scoring_llm_used"] = llm_used
        self.ctx.metrics["scoring_rules_used"] = rules_used

        return scored
