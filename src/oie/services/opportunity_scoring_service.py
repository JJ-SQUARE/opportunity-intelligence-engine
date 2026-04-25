from __future__ import annotations

from typing import Any, Dict, List, Optional

from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import ProviderExecutionService
from oie.services.job_text_service import safe_job_description
from oie.utils.domain_filters import is_job_board_domain, normalize_domain

from oie.orchestration.run_context import RunContext


CLASSIFICATION_WEIGHTS = {
    "end_client": 20,
    "consulting": -20,
    "staffing": -25,
    "marketplace": -12,
    "job_board": -20,
    "competitor": -30,
    "unknown": -5,
    "": 0,
}

PRIORITY_INDUSTRY_TERMS = {
    "banking and financial services",
    "banking",
    "financial services",
    "bfsi",
    "insurance",
    "aerospace",
    "airlines",
    "aviation",
    "technology",
    "information technology",
    "information technology and services",
    "computer software",
    "software",
    "healthcare",
    "life sciences",
    "hospital",
    "medical",
    "logistics",
    "transportation",
    "supply chain",
}

SECONDARY_INDUSTRY_TERMS = {
    "retail",
    "ecommerce",
    "consumer goods",
    "manufacturing",
    "telecommunications",
}

PRIORITY_REGION_TERMS = {
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
    "dominican republic",
    "republica dominicana",
    "bolivia",
    "paraguay",
}

TARGET_STACK_TERMS = {
    "node",
    "node.js",
    "react",
    "python",
    "java",
    "aws",
    "azure",
    "gcp",
    "cloud",
    "ai",
    "artificial intelligence",
    "machine learning",
    "microservices",
    "legacy migration",
    "monolith",
    "monolith to cloud",
}

SENIOR_SIGNAL_TERMS = {
    "senior",
    "sr",
    "lead",
    "staff",
    "principal",
    "architect",
    "engineering manager",
    "head",
    "director",
    "vp",
    "cto",
    "cdo",
    "coo",
}

NEGATIVE_SIGNAL_TERMS = {
    "junior",
    "jr",
    "trainee",
    "intern",
    "internship",
    "practicante",
    "pasante",
    "entry level",
    "direct hire only",
    "no agencies",
    "no agency",
    "hiring freeze",
    "layoff",
    "layoffs",
    "budget cuts",
}

COMPETITOR_HINTS = {
    "babel group",
    "bairesdev",
    "globant",
    "michael page",
    "pagegroup",
    "softserve",
    "softtek",
    "staffing",
    "recruiting",
    "talent solutions",
    "outsourcing",
    "outstaffing",
    "software consulting",
    "software consultancy",
    "nearshore staffing",
    "staff augmentation agency",
}

CLASSIFICATION_ALIASES = {
    "product_company": "end_client",
    "staffing_agency": "staffing",
    "outsourcing": "consulting",
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

    def _normalize_text(self, value: Any) -> str:
        return " ".join(str(value or "").strip().lower().replace("/", " ").replace("-", " ").split())

    def _jobs_text(self, company: Dict[str, Any]) -> str:
        jobs = company.get("jobs") or []
        parts: List[str] = []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            parts.extend(
                [
                    str(job.get("title") or ""),
                    safe_job_description(job),
                    str(job.get("location") or ""),
                ]
            )
        return self._normalize_text(" | ".join(parts))

    def _combined_company_text(self, company: Dict[str, Any]) -> str:
        parts = [
            company.get("company_display"),
            company.get("company"),
            company.get("company_type_ai"),
            company.get("industry"),
            company.get("company_description"),
            company.get("resolved_domain"),
            company.get("linkedin_company_url"),
            self._jobs_text(company),
        ]
        return self._normalize_text(" | ".join(str(part or "") for part in parts))

    def _has_minimum_llm_scoring_evidence(self, company: Dict[str, Any]) -> bool:
        jobs = company.get("jobs") or []
        has_jobs_text = any(
            isinstance(job, dict) and (
                str(job.get("title") or "").strip()
                or str(job.get("description") or "").strip()
                or str(job.get("location") or "").strip()
            )
            for job in jobs
        )

        # Para end_client permitimos pasar a LLM con evidencia mínima más liviana,
        # porque el score puede depender de openings / mix / contexto comercial
        # aunque todavía no haya enrichment completo.
        company_type = self._normalized_company_type(company.get("company_type_ai") or "")
        if company_type == "end_client":
            return any(
                [
                    str(company.get("company_display") or company.get("company") or "").strip(),
                    str(company.get("industry") or "").strip(),
                    str(company.get("company_description") or "").strip(),
                    str(company.get("resolved_domain") or "").strip(),
                    str(company.get("linkedin_company_url") or "").strip(),
                    has_jobs_text,
                    int(company.get("total_openings", 0) or 0) > 0,
                    int(company.get("remote_jobs", 0) or 0) > 0,
                    int(company.get("contractor_jobs", 0) or 0) > 0,
                    bool(company.get("multi_source_signal", False)),
                ]
            )

        return any(
            [
                str(company.get("industry") or "").strip(),
                str(company.get("company_description") or "").strip(),
                str(company.get("resolved_domain") or "").strip(),
                str(company.get("linkedin_company_url") or "").strip(),
                has_jobs_text,
            ]
        )

    def _has_real_icp_evidence(self, company: Dict[str, Any]) -> bool:
        combined_text = self._combined_company_text(company)
        company_type = self._normalized_company_type(company.get("company_type_ai") or "")
        total_openings = int(company.get("total_openings", 0) or 0)
        classification_confidence = float(company.get("classification_confidence_ai") or 0.0)

        priority_hits = self._count_term_hits(combined_text, PRIORITY_INDUSTRY_TERMS)
        secondary_hits = self._count_term_hits(combined_text, SECONDARY_INDUSTRY_TERMS)
        stack_hits = self._count_term_hits(combined_text, TARGET_STACK_TERMS)
        senior_hits = self._count_term_hits(combined_text, SENIOR_SIGNAL_TERMS)

        has_priority_industry = priority_hits >= 1
        has_stack_or_seniority = stack_hits >= 1 or senior_hits >= 1
        has_strong_openings_signal = total_openings >= 2 and (stack_hits >= 1 or senior_hits >= 1)
        is_confident_end_client = company_type == "end_client" and classification_confidence >= 0.7

        if has_priority_industry and has_stack_or_seniority:
            return True

        if priority_hits >= 2:
            return True

        if stack_hits >= 2 and senior_hits >= 1 and total_openings >= 2:
            return True

        if is_confident_end_client and (has_priority_industry or has_strong_openings_signal):
            return True

        # Industria secundaria por sí sola no basta para ICP real.
        if secondary_hits >= 1 and priority_hits == 0:
            return False

        return False

    def _count_term_hits(self, text: str, terms: set[str]) -> int:
        return sum(1 for term in terms if term in text)

    def _is_competitor_or_vendor(self, company: Dict[str, Any], text: str | None = None) -> bool:
        company_type = self._normalized_company_type(company.get("company_type_ai") or "")
        if company.get("benchmark_only") or company_type == "competitor":
            return True
        if company_type in {"staffing", "consulting"}:
            return True

        haystack = text or self._combined_company_text(company)
        return any(hint in haystack for hint in COMPETITOR_HINTS)

    def _industry_fit_score(self, company: Dict[str, Any], text: str) -> int:
        company_type = self._normalized_company_type(company.get("company_type_ai") or "")
        if company_type in {"consulting", "staffing", "job_board", "marketplace", "competitor"}:
            return 0

        hits = self._count_term_hits(text, PRIORITY_INDUSTRY_TERMS)
        if hits > 0:
            return 30

        secondary_hits = self._count_term_hits(text, SECONDARY_INDUSTRY_TERMS)
        if secondary_hits > 0:
            return 16

        return 6 if company_type == "end_client" and text else 0

    def _region_fit_score(self, company: Dict[str, Any], text: str) -> int:
        hits = self._count_term_hits(text, PRIORITY_REGION_TERMS)
        if hits > 0:
            return 10

        jobs = company.get("jobs") or []
        nearshore = any(bool((job or {}).get("nearshore_friendly")) for job in jobs if isinstance(job, dict))
        if nearshore:
            return 7

        return 0

    def _company_scale_score(self, company: Dict[str, Any], text: str) -> int:
        size_text = self._normalize_text(company.get("company_size") or company.get("employee_range") or "")
        for token in ("1001", "5001", "10000", "enterprise", "4000", "5000"):
            if token in size_text:
                return 10
        for token in ("201", "501", "1000", "mid market", "mid-market"):
            if token in size_text:
                return 7

        if "4000" in text or "4,000" in str(company.get("company_description") or ""):
            return 10

        return 0

    def _role_seniority_score(self, company: Dict[str, Any], text: str) -> int:
        openings = int(company.get("total_openings", 0) or 0)
        senior_hits = self._count_term_hits(text, SENIOR_SIGNAL_TERMS)
        if senior_hits >= 2 and openings >= 2:
            return 10
        if senior_hits >= 1:
            return 7
        return 0

    def _pain_urgency_score(self, company: Dict[str, Any], text: str) -> int:
        openings = int(company.get("total_openings", 0) or 0)
        stack_hits = self._count_term_hits(text, TARGET_STACK_TERMS)
        senior_hits = self._count_term_hits(text, SENIOR_SIGNAL_TERMS)

        score = 0
        if openings >= 5:
            score += 10
        elif openings >= 2:
            score += 6
        elif openings == 1:
            score += 3

        if stack_hits >= 3:
            score += 8
        elif stack_hits >= 1:
            score += 4

        if senior_hits >= 2:
            score += 5
        elif senior_hits >= 1:
            score += 2

        if any(term in text for term in ("urgent", "critical role", "immediate start", "legacy migration", "monolith to cloud")):
            score += 4

        return min(score, 25)

    def _negative_signals_penalty(self, company: Dict[str, Any], text: str) -> int:
        penalty = 0
        negative_hits = self._count_term_hits(text, NEGATIVE_SIGNAL_TERMS)

        if negative_hits >= 2:
            penalty -= 10
        elif negative_hits == 1:
            penalty -= 5

        openings = int(company.get("total_openings", 0) or 0)
        senior_hits = self._count_term_hits(text, SENIOR_SIGNAL_TERMS)
        if openings <= 1 and senior_hits == 0:
            penalty -= 3

        return max(penalty, -15)

    def _competitor_penalty(self, company: Dict[str, Any], text: str) -> int:
        return -30 if self._is_competitor_or_vendor(company, text) else 0

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


    def _is_commercially_usable_domain(self, domain: Any) -> bool:
        normalized = normalize_domain(str(domain or "").strip().lower())
        if not normalized:
            return False
        return not is_job_board_domain(normalized)

    def _has_reachability_signal(self, company: Dict[str, Any]) -> bool:
        validation_status = str(company.get("domain_validation_status") or "").strip().lower()
        resolved_domain = str(company.get("resolved_domain") or "").strip().lower()
        linkedin_company_url = str(company.get("linkedin_company_url") or "").strip()
        enrichment_source = str(company.get("enrichment_source") or "").strip().lower()

        if validation_status == "accepted" and self._is_commercially_usable_domain(resolved_domain):
            return True
        if linkedin_company_url:
            return True
        if enrichment_source == "apollo":
            return True
        return False

    def _has_explicit_reachability_gap(self, company: Dict[str, Any]) -> bool:
        validation_status = str(company.get("domain_validation_status") or "").strip().lower()
        resolved_domain = str(company.get("resolved_domain") or "").strip().lower()
        linkedin_company_url = str(company.get("linkedin_company_url") or "").strip()
        enrichment_source = str(company.get("enrichment_source") or "").strip().lower()

        if validation_status in {"rejected", "review"}:
            return True
        if validation_status == "accepted" and not self._is_commercially_usable_domain(resolved_domain) and not linkedin_company_url and enrichment_source != "apollo":
            return True

        # Solo consideramos gap explícito cuando sí hay señales del pipeline
        # y aun así ninguna evidencia de reachability comercial útil.
        has_any_reachability_field = any(
            [
                validation_status,
                resolved_domain,
                linkedin_company_url,
                enrichment_source,
            ]
        )
        return has_any_reachability_field and not self._has_reachability_signal(company)

    def _apply_scoring_guardrails(
        self,
        company: Dict[str, Any],
        scored: Dict[str, Any],
    ) -> Dict[str, Any]:
        guarded = dict(scored)

        def _as_float(value: Any, default: float = 0.0) -> float:
            try:
                return float(value if value is not None else default)
            except Exception:
                return default

        company_type = self._normalized_company_type(company.get("company_type_ai") or "")
        classification_confidence = _as_float(company.get("classification_confidence_ai"), 0.0)

        score = max(0.0, min(_as_float(guarded.get("opportunity_score"), 0.0), 100.0))
        score_icp_fit = _as_float(guarded.get("score_icp_fit"), 0.0)
        score_pain_urgency = _as_float(guarded.get("score_pain_urgency"), 0.0)
        buyer_persona_fit = str(guarded.get("buyer_persona_fit") or "").strip().lower()
        reason = str(guarded.get("opportunity_score_reason") or guarded.get("reason") or "").strip()

        icp_bucket = str(guarded.get("icp_bucket") or "").strip().lower()
        commercial_bucket = str(guarded.get("commercial_bucket") or guarded.get("opportunity_label") or "").strip().lower()
        pain_urgency = str(guarded.get("pain_urgency") or "").strip().lower()
        recommended_service = str(guarded.get("recommended_service") or guarded.get("primary_service_fit") or "").strip().lower()

        if icp_bucket not in {"strong", "medium", "weak"}:
            icp_bucket = "strong" if score_icp_fit >= 24 else "medium" if score_icp_fit >= 12 else "weak"
        if pain_urgency not in {"high", "medium", "low"}:
            pain_urgency = "high" if score_pain_urgency >= 18 else "medium" if score_pain_urgency >= 8 else "low"
        if commercial_bucket not in {"high", "medium", "low"}:
            commercial_bucket = self._normalize_label(int(round(score)), None)
        if not recommended_service:
            recommended_service = str(guarded.get("primary_service_fit") or "unknown").strip().lower()

        has_reachability = self._has_reachability_signal(company)
        has_explicit_reachability_gap = self._has_explicit_reachability_gap(company)

        vendor_like = self._is_competitor_or_vendor(company)
        has_real_icp = (
            not vendor_like
            and (
                score_icp_fit >= 16
                or (
                    score_pain_urgency >= 12
                    and company_type == "end_client"
                )
                or self._has_real_icp_evidence(company)
            )
        )

        if has_real_icp:
            icp_fit_bucket = "strong"
        elif score_icp_fit >= 8:
            icp_fit_bucket = "medium"
        else:
            icp_fit_bucket = "weak"

        guarded["has_real_icp"] = bool(has_real_icp)
        guarded["icp_fit_bucket"] = icp_fit_bucket

        if has_reachability:
            reachability_status = "reachable"
        elif has_explicit_reachability_gap:
            reachability_status = "blocked"
        else:
            reachability_status = "unknown"

        guarded["reachability_status"] = reachability_status
        guarded["reachability_ready"] = bool(has_reachability)

        reason_additions: List[str] = []

        if icp_bucket == "weak" and score > 44:
            score = 44.0
            commercial_bucket = "low"
            reason_additions.append("Cap aplicado por icp_bucket weak.")
        elif icp_bucket == "medium" and score > 74:
            score = 74.0
            commercial_bucket = "medium"
            reason_additions.append("Cap aplicado por icp_bucket medium.")

        if pain_urgency == "low" and score > 54:
            score = 54.0
            commercial_bucket = "medium"
            reason_additions.append("Cap aplicado por pain_urgency low.")

        if buyer_persona_fit == "low" and score > 55:
            score = 55.0
            commercial_bucket = "medium"
            reason_additions.append("Cap aplicado por buyer_persona_fit low.")

        if company_type in {"competitor", "staffing", "consulting", "marketplace", "job_board"}:
            guarded["score_penalty_competitor"] = min(
                _as_float(guarded.get("score_penalty_competitor"), 0.0),
                -30.0,
            )
            if score > 25:
                score = 25.0
            reason_additions.append("Vendor-like / competitor cap aplicado.")

        if buyer_persona_fit == "low" and score > 54:
            score = 54.0
            reason_additions.append("Buyer persona débil; cap aplicado.")

        if has_real_icp and has_explicit_reachability_gap and score > 64:
            score = 64.0
            reason_additions.append("Cap aplicado por reachability insuficiente.")

        if not has_real_icp:
            if has_reachability:
                if company_type == "end_client":
                    if score > 54:
                        score = 54.0
                    reason_additions.append("Reachable end_client con evidencia ICP insuficiente; cap aplicado.")
                else:
                    if score > 49:
                        score = 49.0
                    reason_additions.append("Cap aplicado por evidencia ICP insuficiente.")
            elif has_explicit_reachability_gap:
                if score > 39:
                    score = 39.0
                reason_additions.append("Cap aplicado por falta de reachability y evidencia ICP real.")
            else:
                if company_type == "end_client":
                    if score > 54:
                        score = 54.0
                    reason_additions.append("Cap aplicado por evidencia ICP insuficiente.")
                else:
                    if score > 49:
                        score = 49.0
                    reason_additions.append("Cap aplicado por evidencia ICP insuficiente.")

        if (
            company_type == "end_client"
            and has_reachability
            and classification_confidence > 0
            and classification_confidence < 0.75
            and score > 54
        ):
            score = 54.0
            reason_additions.append("Reachable end_client con clasificación débil; cap aplicado.")

        if (
            company_type == "end_client"
            and has_reachability
            and has_real_icp
            and score_icp_fit >= 24
            and score_pain_urgency >= 15
            and score < 45
        ):
            score = 45.0
            reason_additions.append("Piso aplicado por ICP fuerte con dolor y reachability.")

        score = max(0.0, min(score, 100.0))

        if company_type in {"", "unknown"} and not has_real_icp:
            label = "low"
        elif score >= 75:
            label = "high"
        elif score >= 45:
            label = "medium"
        else:
            label = "low"

        if company_type == "end_client" and score >= 45:
            label = "medium" if score < 75 else "high"

        if reason_additions:
            reason = (reason + " " + " ".join(reason_additions)).strip()

        guarded["opportunity_score"] = int(round(score))
        guarded["opportunity_label"] = label
        guarded["commercial_bucket"] = label
        guarded["icp_bucket"] = icp_bucket
        guarded["pain_urgency"] = pain_urgency
        guarded["recommended_service"] = recommended_service
        guarded["primary_service_fit"] = recommended_service
        guarded["reason"] = reason
        guarded["opportunity_score_reason"] = reason
        return guarded

    def _should_try_llm_scoring(self, company: Dict[str, Any]) -> bool:
        if self.ctx.flags.get("no_llm"):
            return False

        if self.provider_control_service is None:
            return False

        registry = getattr(self.provider_control_service, "registry", None)
        if registry is None:
            return False

        try:
            client = registry.get_client("openai")
        except Exception:
            client = None

        if client is None or not hasattr(client, "score_company"):
            return False

        company_type = self._normalized_company_type(company.get("company_type_ai") or "")

        if company.get("benchmark_only"):
            return False

        if company_type in {"competitor", "job_board"}:
            return False

        return self._has_minimum_llm_scoring_evidence(company)

    def _score_company_with_llm(self, company: Dict[str, Any]) -> Dict[str, Any] | None:
        if not self._should_try_llm_scoring(company):
            company_type = self._normalized_company_type(company.get("company_type_ai") or "")
            has_structured_signal = any(
                [
                    str(company.get("industry") or "").strip(),
                    str(company.get("company_description") or "").strip(),
                    str(company.get("resolved_domain") or "").strip(),
                    str(company.get("linkedin_company_url") or "").strip(),
                ]
            )

            if company_type in {"", "unknown"}:
                metric_key = (
                    "scoring_llm_skipped_low_icp_evidence"
                    if has_structured_signal
                    else "scoring_llm_skipped_unknown_weak_evidence"
                )
                self.ctx.metrics[metric_key] = int(self.ctx.metrics.get(metric_key, 0) or 0) + 1
            elif company_type in {"consulting", "staffing", "marketplace"}:
                self.ctx.metrics["scoring_llm_skipped_low_icp_evidence"] = (
                    int(self.ctx.metrics.get("scoring_llm_skipped_low_icp_evidence", 0) or 0) + 1
                )
            return None

        registry = getattr(self.provider_control_service, "registry", None)
        if registry is None:
            return None

        try:
            client = registry.get_client("openai")
        except Exception:
            client = None

        if client is None or not hasattr(client, "score_company"):
            return None

        payload = dict(company)
        payload["scoring_context"] = self._build_scoring_context()

        try:
            result = self.provider_execution_service.execute(
                "openai",
                "score_company",
                client.score_company,
                payload,
            )
        except Exception:
            return None

        if not isinstance(result, dict) or not result:
            return None

        guarded = self._apply_scoring_guardrails(company, result)

        company_type = self._normalized_company_type(company.get("company_type_ai") or "")
        raw_score = float(result.get("opportunity_score") or 0)
        raw_icp = float(result.get("score_icp_fit") or 0)
        raw_pain = float(result.get("score_pain_urgency") or 0)
        raw_penalty = float(result.get("score_penalty_competitor") or 0)

        if (
            company_type == "end_client"
            and raw_score >= 75
            and raw_icp >= 24
            and raw_pain >= 15
            and raw_penalty > -20
            and not self._has_explicit_reachability_gap(company)
        ):
            restored = dict(guarded)
            restored.update(result)
            restored["opportunity_score"] = int(round(raw_score))
            restored["opportunity_label"] = self._normalize_label(int(round(raw_score)), result.get("opportunity_label"))
            restored["opportunity_score_reason"] = str(result.get("opportunity_score_reason") or "").strip()
            return restored

        return guarded

    def _score_company(self, company: Dict[str, Any]) -> Dict[str, Any]:
        total_openings = int(company.get("total_openings", 0) or 0)
        remote_jobs = int(company.get("remote_jobs", 0) or 0)
        contractor_jobs = int(company.get("contractor_jobs", 0) or 0)
        multi_source_signal = bool(company.get("multi_source_signal", False))
        company_type = self._normalized_company_type(company.get("company_type_ai") or "")
        combined_text = self._combined_company_text(company)

        score_openings = min(total_openings * 4, 12)
        score_remote = min(remote_jobs * 2, 6)
        score_contractor = min(contractor_jobs * 2, 6)
        score_multi_source = 4 if multi_source_signal else 0
        score_company_type = CLASSIFICATION_WEIGHTS.get(company_type, 0)

        score_icp_fit = self._industry_fit_score(company, combined_text)
        score_pain_urgency = self._pain_urgency_score(company, combined_text)
        score_region_fit = self._region_fit_score(company, combined_text)
        score_company_scale = self._company_scale_score(company, combined_text)
        score_role_seniority_mix = self._role_seniority_score(company, combined_text)
        score_penalty_competitor = self._competitor_penalty(company, combined_text)
        score_penalty_negative_signals = self._negative_signals_penalty(company, combined_text)

        total_score = (
            score_icp_fit
            + score_pain_urgency
            + score_region_fit
            + score_company_scale
            + score_role_seniority_mix
            + score_penalty_competitor
            + score_penalty_negative_signals
        )

        total_score = max(0, min(total_score, 100))
        label = self._normalize_label(total_score, None)

        primary_service_fit = "talent_as_a_service"
        if any(term in combined_text for term in ("legacy migration", "monolith to cloud", "microservices")):
            primary_service_fit = "agile_solution_delivery"
        elif any(term in combined_text for term in ("support", "maintenance", "operations")):
            primary_service_fit = "managed_it_services"

        buyer_persona_fit = "high" if score_role_seniority_mix >= 7 else "medium" if score_icp_fit >= 16 else "low"

        reason_parts = []
        if score_penalty_competitor <= -30:
            reason_parts.append("Competidor / staffing / consultoría; conservar pero penalizar fuerte.")
        else:
            if score_icp_fit >= 25:
                reason_parts.append("Buen fit sectorial al ICP.")
            elif score_icp_fit <= 10:
                reason_parts.append("Fit sectorial limitado.")
            if score_pain_urgency >= 15:
                reason_parts.append("Señales claras de dolor técnico o capacidad.")
            elif score_pain_urgency <= 6:
                reason_parts.append("Poca evidencia de urgencia.")
            if score_company_scale >= 7:
                reason_parts.append("Tamaño atractivo para Tekton.")
            if score_penalty_negative_signals <= -5:
                reason_parts.append("Hay señales negativas que bajan prioridad.")

        return self._apply_scoring_guardrails(
            company,
            {
                "score_openings": score_openings,
                "score_remote": score_remote,
                "score_contractor": score_contractor,
                "score_multi_source": score_multi_source,
                "score_company_type": score_company_type,
                "score_icp_fit": score_icp_fit,
                "score_pain_urgency": score_pain_urgency,
                "score_region_fit": score_region_fit,
                "score_company_scale": score_company_scale,
                "score_role_seniority_mix": score_role_seniority_mix,
                "score_penalty_competitor": score_penalty_competitor,
                "score_penalty_negative_signals": score_penalty_negative_signals,
                "opportunity_score": total_score,
                "opportunity_label": label,
                "primary_service_fit": primary_service_fit,
                "buyer_persona_fit": buyer_persona_fit,
                "opportunity_score_reason": " ".join(reason_parts[:2]).strip(),
                "scoring_provider": "rules",
                "scoring_model": "",
                "scoring_mode": "fallback_rules",
            },
        )

    def score_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        scored: List[Dict[str, Any]] = []

        llm_used = 0
        rules_used = 0

        for company in companies:
            llm_score = self._score_company_with_llm(company)

            enriched = dict(company)

            if llm_score:
                rule_components = self._score_company(company)
                enriched.update(rule_components)
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
