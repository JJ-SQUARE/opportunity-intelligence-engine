from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import ProviderExecutionService
from oie.services.job_text_service import safe_job_description
from oie.utils.domain_filters import is_job_board_domain


RULE_KEYWORDS = {
    "staffing": [
        "staffing",
        "staffing and recruiting",
        "recruiting",
        "recruitment",
        "talent solutions",
        "headhunting",
        "executive search",
        "talent partner",
        "talent acquisition",
        "reclutamiento especializado",
        "recruitment firm",
        "staffing firm",
    ],
    "consulting": [
        "outsourcing",
        "outsource",
        "outstaffing",
        "staff augmentation",
        "nearshore software",
        "nearshore development",
        "dedicated teams",
        "software outsourcing",
        "technology outsourcing",
        "consulting",
        "consultancy",
        "professional services",
        "advisory",
        "technology consulting",
        "software consulting",
        "software consultancy",
        "software development services",
        "custom software development",
        "digital transformation services",
        "it services",
        "it service provider",
        "systems integrator",
    ],
    "marketplace": [
        "marketplace",
        "two-sided marketplace",
        "talent marketplace",
    ],
    "job_board": [
        "job board",
        "jobs board",
        "career portal",
        "job search",
        "find jobs",
        "empleos",
        "vacantes",
        "jobgether",
    ],
}

END_CLIENT_HINTS = {
    "saas",
    "platform",
    "product company",
    "software product",
    "builds software products",
    "banking and financial services",
    "insurance",
    "healthcare",
    "life sciences",
    "logistics",
    "transportation",
    "airlines",
    "aviation",
    "computer software",
    "software company",
    "fintech",
    "proptech",
    "healthtech",
    "edtech",
}


COMPETITOR_HINTS = {
    "babel group",
    "bairesdev",
    "globant",
    "michael page",
    "pagegroup",
    "softserve",
    "softtek",
}

PLACEHOLDER_COMPANY_VALUES = {
    "",
    "unknown",
    "confidential",
    "stealth",
    "undisclosed",
    "n/a",
    "na",
}

PLACEHOLDER_COMPANY_PATTERNS = (
    "empresa confidencial",
    "compañía confidencial",
    "cia confidencial",
    "confidential company",
    "stealth company",
    "undisclosed company",
)

CLASSIFICATION_ALIASES = {
    "outsourcing": "consulting",
    "staffing_agency": "staffing",
}


class CompanyClassificationService:
    def __init__(
        self,
        ctx: RunContext,
        provider_control_service: ProviderControlService,
    ) -> None:
        self.ctx = ctx
        self.provider_control_service = provider_control_service
        self.provider_execution_service = ProviderExecutionService(ctx, provider_control_service)

    def _normalize_classification(self, value: Any) -> str:
        normalized = str(value or "").strip().lower()
        return CLASSIFICATION_ALIASES.get(normalized, normalized)

    def _classification_text(self, company: Dict[str, Any]) -> str:
        jobs = company.get("jobs") or []
        job_parts: List[str] = []

        for job in jobs:
            if not isinstance(job, dict):
                continue
            job_parts.extend(
                [
                    str(job.get("title") or ""),
                    safe_job_description(job),
                    str(job.get("location") or ""),
                ]
            )

        return " ".join(
            [
                str(company.get("company_display") or ""),
                str(company.get("company") or ""),
                str(company.get("company_description") or ""),
                str(company.get("industry") or ""),
                str(company.get("resolved_domain") or ""),
                str(company.get("linkedin_company_url") or ""),
                *job_parts,
            ]
        ).lower()

    def _has_placeholder_company_name(self, company: Dict[str, Any]) -> bool:
        values = [
            str(company.get("company_display") or "").strip().lower(),
            str(company.get("company") or "").strip().lower(),
        ]

        for value in values:
            if not value:
                continue
            if value in PLACEHOLDER_COMPANY_VALUES:
                return True
            if any(pattern in value for pattern in PLACEHOLDER_COMPANY_PATTERNS):
                return True

        return False

    def _has_minimum_llm_classification_evidence(self, company: Dict[str, Any]) -> bool:
        if str(company.get("company_description") or "").strip():
            return True
        if str(company.get("industry") or "").strip():
            return True
        if str(company.get("resolved_domain") or "").strip():
            return True
        if str(company.get("linkedin_company_url") or "").strip():
            return True

        jobs = company.get("jobs") or []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            if (
                str(job.get("title") or "").strip()
                or safe_job_description(job)
                or str(job.get("location") or "").strip()
            ):
                return True

        return False

    def _has_end_client_evidence(self, company: Dict[str, Any], text: str | None = None) -> bool:
        haystack = (text or self._classification_text(company)).strip().lower()
        if not haystack:
            return False

        if any(hint in haystack for hint in COMPETITOR_HINTS):
            return False

        for keywords in RULE_KEYWORDS.values():
            if any(keyword in haystack for keyword in keywords):
                return False

        industry = str(company.get("industry") or "").strip().lower()
        description = str(company.get("company_description") or "").strip().lower()
        jobs = company.get("jobs") or []

        hint_hits = sum(1 for hint in END_CLIENT_HINTS if hint in haystack)
        has_product_language = any(term in description for term in ("product", "platform", "saas", "software"))
        has_clear_industry = bool(industry and any(hint in industry for hint in END_CLIENT_HINTS))
        has_build_language = any(
            term in description
            for term in ("builds", "develops", "operates", "offers", "provides")
        )
        has_hiring_signal = any(
            isinstance(job, dict) and (
                str(job.get("title") or "").strip()
                or safe_job_description(job)
            )
            for job in jobs
        )

        if hint_hits >= 2:
            return True

        if has_clear_industry and (has_product_language or has_build_language or has_hiring_signal):
            return True

        if has_product_language and has_build_language:
            return True

        return False

    def _rule_based_classification(self, company: Dict[str, Any]) -> Dict[str, Any] | None:
        domain = str(company.get("resolved_domain") or "").strip().lower()
        text = self._classification_text(company)

        if self._has_placeholder_company_name(company) and not self._has_minimum_llm_classification_evidence(company):
            return {
                "classification": "unknown",
                "confidence": 0.0,
                "provider": "rules",
                "reason": "Placeholder or confidential company with insufficient classification evidence.",
            }

        if domain and is_job_board_domain(domain):
            return {
                "classification": "job_board",
                "confidence": 0.95,
                "provider": "rules",
                "reason": "Resolved domain is recognized as a job board or wrapper domain.",
            }

        if domain and any(hint in domain for hint in COMPETITOR_HINTS):
            return {
                "classification": "competitor",
                "confidence": 0.95,
                "provider": "rules",
                "reason": "Company/domain matches a configured competitor hint.",
            }

        if any(hint in text for hint in COMPETITOR_HINTS):
            return {
                "classification": "competitor",
                "confidence": 0.95,
                "provider": "rules",
                "reason": "Company text matches a configured competitor hint.",
            }

        for company_type, keywords in RULE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    normalized_type = self._normalize_classification(company_type)
                    confidence = 0.9 if normalized_type in {"staffing", "consulting", "job_board"} else 0.8
                    return {
                        "classification": normalized_type,
                        "confidence": confidence,
                        "provider": "rules",
                        "reason": f"Matched rule keyword: {keyword}.",
                    }

        if self._has_end_client_evidence(company, text):
            return {
                "classification": "end_client",
                "confidence": 0.72,
                "provider": "rules",
                "reason": "Matched product/company evidence consistent with an end client.",
            }

        if text.strip():
            return {
                "classification": "unknown",
                "confidence": 0.2,
                "provider": "rules",
                "reason": "Evidence exists but rules could not classify the company confidently.",
            }

        return None

    def _should_use_rule_override(
        self,
        rule_result: Dict[str, Any] | None,
        company: Dict[str, Any] | None = None,
    ) -> bool:
        if not rule_result:
            return False

        classification = str(rule_result.get("classification") or "").strip().lower()
        confidence = float(rule_result.get("confidence") or 0.0)

        if classification in {"competitor", "staffing", "job_board", "consulting", "marketplace"} and confidence >= 0.8:
            return True

        if classification == "end_client" and confidence >= 0.72:
            company = company or {}
            description = str(company.get("company_description") or "").strip().lower()
            industry = str(company.get("industry") or "").strip().lower()
            domain = str(company.get("resolved_domain") or "").strip().lower()
            jobs = company.get("jobs") or []

            has_description = bool(description)
            has_industry = bool(industry)
            has_domain = bool(domain)

            has_job_titles = any(
                isinstance(job, dict) and str(job.get("title") or "").strip()
                for job in jobs
            )
            has_job_descriptions = any(
                isinstance(job, dict) and bool(safe_job_description(job))
                for job in jobs
            )
            has_product_language = any(
                term in description
                for term in ("product", "products", "platform", "platforms", "saas", "software")
            )
            has_build_language = any(
                term in description
                for term in ("builds", "develops", "operates", "offers", "provides")
            )
            has_priority_industry = any(
                hint in industry
                for hint in END_CLIENT_HINTS
            )

            # Override fuerte solo cuando sí existen señales operativas reales
            # además de descripción/industria/dominio.
            if (
                has_description
                and has_industry
                and has_domain
                and has_job_titles
                and (
                    has_job_descriptions
                    or has_product_language
                    or has_build_language
                    or has_priority_industry
                )
            ):
                return True

        return False

    def classify_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self.ctx.flags.get("no_llm"):
            classified = []
            for company in companies:
                enriched = dict(company)
                company_type = str(enriched.get("company_type_ai") or "").strip().lower()

                if enriched.get("benchmark_only") or company_type == "competitor":
                    enriched["company_type_ai"] = "competitor"
                    enriched["classification_confidence_ai"] = float(
                        enriched.get("classification_confidence_ai") or 1.0
                    )
                    enriched["classification_provider"] = (
                        enriched.get("classification_provider")
                        or enriched.get("classification_source")
                        or "benchmark_config"
                    )
                    classified.append(enriched)
                    continue

                rule_result = self._rule_based_classification(company)
                if rule_result:
                    enriched["company_type_ai"] = rule_result["classification"]
                    enriched["classification_confidence_ai"] = rule_result["confidence"]
                    enriched["classification_provider"] = rule_result["provider"]
                    enriched["classification_reason"] = rule_result.get("reason")
                classified.append(enriched)

            self.ctx.metrics["company_classification_skipped_no_llm"] = True
            self.ctx.metrics["companies_classified"] = len(classified)
            return classified

        client = self.provider_control_service.registry.get_client("openai")
        if client is None:
            self.ctx.metrics["company_classification_skipped_no_client"] = True
            return companies

        classified: List[Dict[str, Any]] = []

        for company in companies:
            enriched = dict(company)
            company_type = str(enriched.get("company_type_ai") or "").strip().lower()

            if enriched.get("benchmark_only"):
                enriched["company_type_ai"] = "competitor"
                enriched["classification_confidence_ai"] = float(
                    enriched.get("classification_confidence_ai") or 1.0
                )
                enriched["classification_provider"] = (
                    enriched.get("classification_provider")
                    or enriched.get("classification_source")
                    or "benchmark_config"
                )
                enriched["classification_reason"] = (
                    enriched.get("classification_reason")
                    or "Company is configured as benchmark-only competitor."
                )
                classified.append(enriched)
                continue

            rule_result = self._rule_based_classification(company)
            if not self._has_minimum_llm_classification_evidence(company):
                self.ctx.metrics["company_classification_llm_skipped_low_evidence"] = (
                    int(self.ctx.metrics.get("company_classification_llm_skipped_low_evidence", 0) or 0) + 1
                )
                result = rule_result or {
                    "classification": "unknown",
                    "confidence": 0.0,
                    "provider": "rules",
                    "reason": "Insufficient evidence for AI classification.",
                }
            else:
                try:
                    result = self.provider_execution_service.execute(
                        "openai",
                        "classify_company",
                        client.classify_company,
                        company,
                        cost=1,
                    )
                    self.ctx.metrics["company_classification_ai_used"] = (
                        int(self.ctx.metrics.get("company_classification_ai_used", 0) or 0) + 1
                    )
                except Exception:
                    result = rule_result or {
                        "classification": "unknown",
                        "confidence": 0.0,
                        "provider": "fallback_rules",
                        "reason": "AI classification failed and no rule-based classification was available.",
                    }
                    self.ctx.metrics["company_classification_fallback_rules_used"] = (
                        int(self.ctx.metrics.get("company_classification_fallback_rules_used", 0) or 0) + 1
                    )

            enriched["company_type_ai"] = self._normalize_classification(result.get("classification"))
            enriched["classification_confidence_ai"] = result.get("confidence")
            enriched["classification_provider"] = result.get("provider")
            enriched["classification_reason"] = result.get("reason")
            classified.append(enriched)

        self.ctx.metrics["companies_classified"] = len(classified)
        return classified
