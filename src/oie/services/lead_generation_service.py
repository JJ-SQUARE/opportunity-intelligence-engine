from __future__ import annotations

import re
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.services.cached_provider_service import CachedProviderService
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import (
    ProviderExecutionBlockedError,
    ProviderExecutionError,
    ProviderExecutionService,
)
from oie.utils.domain_filters import is_job_board_domain


TARGET_TITLES = [
    "CTO",
    "Chief Technology Officer",
    "CIO",
    "Chief Information Officer",
    "Chief Digital Officer",
    "Chief Product Officer",
    "CEO",
    "Chief Executive Officer",
    "Founder",
    "Co-Founder",
    "Managing Director",
    "VP Engineering",
    "VP of Engineering",
    "Vice President Engineering",
    "Vice President of Engineering",
    "VP Technology",
    "VP of Technology",
    "Vice President Technology",
    "Vice President of Technology",
    "VP Software Engineering",
    "Vice President Software Engineering",
    "VP Product Engineering",
    "VP Digital",
    "VP Information Technology",
    "VP IT",
    "SVP Engineering",
    "SVP Technology",
    "AVP Engineering",
    "AVP Technology",
    "VPE",
    "Head of Engineering",
    "Head of Technology",
    "Head of Software Engineering",
    "Head of Product Engineering",
    "Head of Platform Engineering",
    "Head of Applications",
    "Head of Development",
    "Head of IT",
    "Head of Information Technology",
    "Head of Digital",
    "Head of Data",
    "Head of Infrastructure",
    "Head of Architecture",
    "Head of R&D",
    "Head of Research and Development",
    "Director of Engineering",
    "Engineering Director",
    "Director of Technology",
    "Technology Director",
    "Director of Software Engineering",
    "Director of Product Engineering",
    "Director of Platform Engineering",
    "Director of Development",
    "Director of Applications",
    "Director of IT",
    "IT Director",
    "Director of Information Technology",
    "Director of Digital",
    "Director of Data Engineering",
    "Director of Infrastructure",
    "Director of Architecture",
    "Technical Director",
    "Engineering Manager",
    "Software Engineering Manager",
    "Development Manager",
    "IT Manager",
    "Technical Manager",
    "Technical Lead",
    "Tech Lead",
    "Engineering Lead",
    "Software Architect",
    "Solutions Architect",
    "Enterprise Architect",
]

EXCLUDED_TITLE_TERMS = [
    "recruiter",
    "recruiting",
    "talent",
    "talent acquisition",
    "talent partner",
    "sourcer",
    "staffing specialist",
    "staffing manager",
    "hr",
    "human resources",
    "people",
    "people ops",
    "people operations",
    "people partner",
    "people business partner",
    "compliance",
    "operations",
    "operating officer",
    "finance",
    "financial",
    "accounting",
    "controller",
    "legal",
    "counsel",
    "marketing",
    "growth",
    "brand",
    "sales",
    "account executive",
    "business development",
    "customer success",
    "support",
    "procurement",
    "purchasing",
    "buyer",
    "supply chain",
    "office manager",
    "administrative",
    "administrator",
    "executive assistant",
    "intern",
    "trainee",
    "junior",
    "student",
    "qa analyst",
    "test engineer",
    "support engineer",
    "help desk",
]

TECHNICAL_TITLE_TERMS = [
    "technology",
    "engineering",
    "software engineering",
    "product engineering",
    "platform engineering",
    "application development",
    "software development",
    "development",
    "technical",
    "it",
    "information technology",
    "digital",
    "architecture",
    "solutions architecture",
    "enterprise architecture",
    "infrastructure",
    "cloud",
    "data",
    "data engineering",
    "platform",
    "r&d",
    "research and development",
    "cto",
    "cio",
    "cdo",
    "cpo",
    "vpe",
    "vp engineering",
    "vp technology",
    "head of engineering",
    "head of technology",
    "director of engineering",
    "director of technology",
    "engineering director",
    "technology director",
    "engineering manager",
    "software engineering manager",
    "tech lead",
    "technical lead",
    "architect",
]

SENIOR_TITLE_TERMS = [
    "chief",
    "cto",
    "cio",
    "cdo",
    "cpo",
    "ceo",
    "founder",
    "co-founder",
    "owner",
    "partner",
    "president",
    "vp",
    "vice president",
    "svp",
    "avp",
    "head",
    "director",
    "manager",
    "lead",
    "principal",
]

GENERIC_EMAIL_PREFIXES = {
    "admin",
    "contact",
    "careers",
    "career",
    "cv",
    "empleo",
    "engineering",
    "hello",
    "hi",
    "hola",
    "hr",
    "info",
    "jobs",
    "marketing",
    "noreply",
    "no-reply",
    "operations",
    "people",
    "press",
    "recruiting",
    "recruitment",
    "sales",
    "support",
    "team",
    "work",
    "workin",
}

SUSPICIOUS_LOCAL_PART_TERMS = {
    "admin",
    "career",
    "careers",
    "contact",
    "empleo",
    "engineering",
    "hello",
    "hola",
    "hr",
    "info",
    "job",
    "jobs",
    "marketing",
    "noreply",
    "no-reply",
    "operations",
    "people",
    "press",
    "recruit",
    "recruiter",
    "recruiting",
    "recruitment",
    "sales",
    "support",
    "team",
    "workin",
}

SENIORITY_HINTS = {
    "cto": 40,
    "chief technology officer": 40,
    "vp engineering": 35,
    "vice president engineering": 35,
    "head of engineering": 34,
    "engineering director": 30,
    "director of engineering": 30,
    "head of product": 24,
}

NAME_TOKEN_RE = re.compile(r"^[a-z]+(?:[._-][a-z]+)+$")
SIMPLE_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LeadGenerationService:
    def __init__(
        self,
        ctx: RunContext,
        provider_control_service: ProviderControlService,
    ) -> None:
        self.ctx = ctx
        self.provider_control_service = provider_control_service
        self.provider_execution_service = ProviderExecutionService(ctx, provider_control_service)
        self.cached_provider_service = CachedProviderService(ctx)

        lead_cfg = self.ctx.config.get("lead_generation", {}) or {}
        self.max_companies_per_run = int(lead_cfg.get("max_companies_per_run", 5))
        self.min_opportunity_score = float(lead_cfg.get("min_opportunity_score", 15))
        self.require_accepted_domain = bool(lead_cfg.get("require_accepted_domain", True))
        self.enable_stub_leads = bool(lead_cfg.get("enable_stub_leads", False))
        self.max_hunter_results_per_company = int(lead_cfg.get("max_hunter_results_per_company", 2))
        self.max_apollo_results_per_company = int(lead_cfg.get("max_apollo_results_per_company", 3))
        self.max_leads_per_company = int(
            lead_cfg.get(
                "max_leads_per_company",
                max(self.max_hunter_results_per_company, self.max_apollo_results_per_company),
            )
        )
        self.hunter_min_email_quality = int(lead_cfg.get("hunter_min_email_quality", 40))

        failed_apollo_lead_domains = self.ctx.provider_state.get("failed_apollo_lead_domains")
        if not isinstance(failed_apollo_lead_domains, set):
            failed_apollo_lead_domains = set()
            self.ctx.provider_state["failed_apollo_lead_domains"] = failed_apollo_lead_domains
        self._failed_apollo_lead_domains = failed_apollo_lead_domains

        failed_hunter_lead_domains = self.ctx.provider_state.get("failed_hunter_lead_domains")
        if not isinstance(failed_hunter_lead_domains, set):
            failed_hunter_lead_domains = set()
            self.ctx.provider_state["failed_hunter_lead_domains"] = failed_hunter_lead_domains
        self._failed_hunter_lead_domains = failed_hunter_lead_domains

    def _is_relevant_title(self, title: str) -> bool:
        value = (title or "").strip().lower()
        if not value:
            return False

        for excluded in EXCLUDED_TITLE_TERMS:
            if excluded in value:
                return False

        normalized = " ".join(
            value.replace("/", " ").replace("-", " ").replace("&", " ").split()
        )

        if any(target.lower() == normalized for target in TARGET_TITLES):
            return True

        has_seniority = any(term in normalized for term in SENIOR_TITLE_TERMS)
        has_technical_scope = any(term in normalized for term in TECHNICAL_TITLE_TERMS)

        return has_seniority and has_technical_scope

    def _priority(self, company: Dict[str, Any]) -> tuple:
        opportunity_score = float(company.get("opportunity_score") or 0.0)
        company_type = (company.get("company_type_ai") or "").strip().lower()
        enriched = bool(company.get("industry") or company.get("employee_range") or company.get("linkedin_company_url"))
        validation_status = (company.get("domain_validation_status") or "").strip().lower()

        return (
            1 if validation_status == "accepted" else 0,
            1 if company_type == "end_client" else 0,
            1 if enriched else 0,
            opportunity_score,
        )

    def _normalize_email(self, email: str) -> str:
        return (email or "").strip().lower()

    def _email_local_part(self, email: str) -> str:
        normalized = self._normalize_email(email)
        if "@" not in normalized:
            return ""
        return normalized.split("@", 1)[0]

    def _is_generic_email(self, email: str) -> bool:
        local = self._email_local_part(email)
        if not local:
            return True

        compact = local.replace(".", "").replace("_", "").replace("-", "")
        if local in GENERIC_EMAIL_PREFIXES or compact in GENERIC_EMAIL_PREFIXES:
            return True

        for token in SUSPICIOUS_LOCAL_PART_TERMS:
            if token in local:
                return True

        return False

    def _email_quality_score(self, email: str, first_name: str = "", last_name: str = "") -> int:
        normalized = self._normalize_email(email)
        if not normalized or not SIMPLE_EMAIL_RE.match(normalized):
            return 0

        local = self._email_local_part(normalized)
        if not local:
            return 0

        if self._is_generic_email(normalized):
            return 0

        score = 20

        if NAME_TOKEN_RE.match(local):
            score += 45
        elif "." in local or "_" in local or "-" in local:
            score += 25

        alpha_chars = sum(1 for c in local if c.isalpha())
        digit_chars = sum(1 for c in local if c.isdigit())

        if alpha_chars >= 6:
            score += 10

        if digit_chars == 0:
            score += 10
        elif digit_chars >= 3:
            score -= 15

        first_name = (first_name or "").strip().lower()
        last_name = (last_name or "").strip().lower()

        if first_name and first_name in local:
            score += 10
        if last_name and last_name in local:
            score += 10

        return max(0, min(score, 100))

    def _lead_title_score(self, title: str) -> int:
        value = (title or "").strip().lower()
        if not value or value == "unknown":
            return 0

        for hint, score in SENIORITY_HINTS.items():
            if hint in value:
                return score

        if "engineer" in value:
            return 8
        if "product" in value:
            return 6
        return 4

    def _build_lead_reason(
        self,
        source: str,
        title: str,
        email_quality: int,
    ) -> str:
        parts: List[str] = []

        if source == "apollo_people":
            parts.append("apollo_match")
        elif source == "hunter_domain_search":
            parts.append("hunter_match")

        if title and title != "Unknown":
            parts.append(f"title:{title}")

        if email_quality > 0:
            parts.append(f"email_quality:{email_quality}")

        return " | ".join(parts)

    def _lead_sort_key(self, lead: Dict[str, Any]) -> tuple:
        title = lead.get("contact_title") or ""
        email_quality = int(lead.get("email_quality_score") or 0)
        linkedin_present = 1 if (lead.get("linkedin_url") or "").strip() else 0
        email_present = 1 if (lead.get("email") or "").strip() else 0
        confidence = float(lead.get("lead_confidence") or 0.0)
        source = lead.get("lead_source") or ""
        source_priority = 1 if source == "hunter_domain_search" else 0

        return (
            self._lead_title_score(title),
            email_quality,
            email_present,
            linkedin_present,
            source_priority,
            confidence,
        )

    def _apollo_has_strong_contact_signal(self, leads: List[Dict[str, Any]]) -> bool:
        for lead in leads:
            if int(lead.get("email_quality_score") or 0) >= self.hunter_min_email_quality:
                return True
            if (lead.get("linkedin_url") or "").strip():
                return True
        return False

    def _combine_company_leads(
        self,
        apollo_leads: List[Dict[str, Any]],
        hunter_leads: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        combined = self._dedupe_leads([*apollo_leads, *hunter_leads])
        combined.sort(key=self._lead_sort_key, reverse=True)
        return combined[: self.max_leads_per_company]

    def _dedupe_leads(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        deduped: List[Dict[str, Any]] = []

        for lead in leads:
            key = (
                (lead.get("company_key") or "").strip(),
                self._normalize_email(lead.get("email") or ""),
                (lead.get("linkedin_url") or "").strip().lower(),
                (lead.get("contact_name") or "").strip().lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(lead)

        return deduped

    def _map_apollo_people(
        self,
        company: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        people = payload.get("people") or payload.get("contacts") or []
        leads: List[Dict[str, Any]] = []
        company_key = company.get("company_key") or ""

        for person in people:
            title = person.get("title") or ""
            if not self._is_relevant_title(title):
                continue

            email = person.get("email") or ""
            email_quality = self._email_quality_score(
                email,
                first_name=person.get("first_name") or "",
                last_name=person.get("last_name") or "",
            )

            leads.append(
                {
                    "company_key": company_key,
                    "company_display": company.get("company_display") or company.get("company") or "",
                    "company_type_ai": company.get("company_type_ai") or "",
                    "industry": company.get("industry") or "",
                    "resolved_domain": company.get("resolved_domain") or "",
                    "company_size": company.get("company_size") or company.get("employee_range") or "",
                    "employee_range": company.get("employee_range") or "",
                    "linkedin_company_url": company.get("linkedin_company_url") or "",
                    "company_description": company.get("company_description") or "",
                    "opportunity_score": company.get("opportunity_score") or 0,
                    "opportunity_label": company.get("opportunity_label") or "",
                    "contact_name": person.get("name") or "",
                    "contact_title": title,
                    "email": email,
                    "linkedin_url": person.get("linkedin_url") or person.get("linkedin") or "",
                    "lead_source": "apollo_people",
                    "lead_confidence": 0.9,
                    "email_quality_score": email_quality,
                    "lead_capture_reason": self._build_lead_reason("apollo_people", title, email_quality),
                }
            )

        leads = self._dedupe_leads(leads)
        leads.sort(key=self._lead_sort_key, reverse=True)
        return leads[: self.max_apollo_results_per_company]

    def _map_hunter_people(
        self,
        company: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        data = payload.get("data") or {}
        emails = data.get("emails") or []

        leads: List[Dict[str, Any]] = []
        filtered_generic = 0
        filtered_low_quality = 0
        company_key = company.get("company_key") or ""

        for item in emails:
            title = item.get("position") or ""
            if title and not self._is_relevant_title(title):
                continue

            email = item.get("value") or ""
            first_name = item.get("first_name") or ""
            last_name = item.get("last_name") or ""
            email_quality = self._email_quality_score(
                email,
                first_name=first_name,
                last_name=last_name,
            )

            if self._is_generic_email(email):
                filtered_generic += 1
                continue

            if email_quality < self.hunter_min_email_quality:
                filtered_low_quality += 1
                continue

            contact_name = " ".join([part for part in [first_name, last_name] if part]).strip()
            if not contact_name:
                contact_name = first_name or email

            title_value = title or "Unknown"
            title_score = self._lead_title_score(title_value)
            confidence = min(0.85, max(0.45, 0.45 + (email_quality / 200.0) + (title_score / 200.0)))

            leads.append(
                {
                    "company_key": company_key,
                    "company_display": company.get("company_display") or company.get("company") or "",
                    "company_type_ai": company.get("company_type_ai") or "",
                    "industry": company.get("industry") or "",
                    "resolved_domain": company.get("resolved_domain") or "",
                    "company_size": company.get("company_size") or company.get("employee_range") or "",
                    "employee_range": company.get("employee_range") or "",
                    "linkedin_company_url": company.get("linkedin_company_url") or "",
                    "company_description": company.get("company_description") or "",
                    "opportunity_score": company.get("opportunity_score") or 0,
                    "opportunity_label": company.get("opportunity_label") or "",
                    "contact_name": contact_name,
                    "contact_title": title_value,
                    "email": email,
                    "linkedin_url": item.get("linkedin") or "",
                    "lead_source": "hunter_domain_search",
                    "lead_confidence": round(confidence, 2),
                    "email_quality_score": email_quality,
                    "lead_capture_reason": self._build_lead_reason("hunter_domain_search", title_value, email_quality),
                }
            )

        leads = self._dedupe_leads(leads)
        leads.sort(
            key=lambda row: (
                self._lead_title_score(row.get("contact_title") or ""),
                int(row.get("email_quality_score") or 0),
                1 if row.get("linkedin_url") else 0,
            ),
            reverse=True,
        )

        self.ctx.metrics["hunter_leads_filtered_generic_email"] = (
            int(self.ctx.metrics.get("hunter_leads_filtered_generic_email", 0)) + filtered_generic
        )
        self.ctx.metrics["hunter_leads_filtered_low_quality"] = (
            int(self.ctx.metrics.get("hunter_leads_filtered_low_quality", 0)) + filtered_low_quality
        )

        return leads[: self.max_hunter_results_per_company]

    def _should_attempt_lead_generation(self, company: Dict[str, Any]) -> bool:
        company_key = company.get("company_key")
        domain = (company.get("resolved_domain") or "").strip().lower()
        validation_status = (company.get("domain_validation_status") or "").strip().lower()
        company_type = (company.get("company_type_ai") or "").strip().lower()
        classification_confidence = float(company.get("classification_confidence_ai") or 0.0)
        opportunity_score = float(company.get("opportunity_score") or 0.0)

        if not company_key or not domain:
            return False

        if is_job_board_domain(domain):
            return False

        if self.require_accepted_domain and validation_status and validation_status != "accepted":
            return False

        if validation_status == "review":
            return False

        if company_type and company_type != "end_client" and classification_confidence >= 0.75:
            return False

        if opportunity_score > 0 and opportunity_score < self.min_opportunity_score:
            return False

        return True

    def _search_apollo_people(self, company: Dict[str, Any]) -> List[Dict[str, Any]]:
        client = self.provider_control_service.registry.get_client("apollo")
        if client is None:
            return []

        domain = (company.get("resolved_domain") or "").strip().lower()
        company_key = company.get("company_key") or ""
        if not domain or not company_key:
            return []
        if domain in self._failed_apollo_lead_domains:
            return []

        try:
            payload = self.cached_provider_service.execute_cached(
                namespace="apollo_people_search",
                cache_payload={"domain": domain, "titles": TARGET_TITLES},
                fn=lambda: self.provider_execution_service.execute(
                    "apollo",
                    "search_people_by_domain_and_titles",
                    client.search_people_by_domain_and_titles,
                    domain,
                    TARGET_TITLES,
                    cost=1,
                ),
            )
        except (ProviderExecutionBlockedError, ProviderExecutionError, ValueError):
            if domain:
                self._failed_apollo_lead_domains.add(domain)
            return []

        return self._map_apollo_people(company, payload)

    def _search_hunter_fallback(self, company: Dict[str, Any]) -> List[Dict[str, Any]]:
        client = self.provider_control_service.registry.get_client("hunter")
        if client is None:
            return []

        domain = (company.get("resolved_domain") or "").strip().lower()
        company_key = company.get("company_key") or ""
        if not domain or not company_key:
            return []
        if domain in self._failed_hunter_lead_domains:
            return []

        try:
            payload = self.cached_provider_service.execute_cached(
                namespace="hunter_domain_search",
                cache_payload={"domain": domain},
                fn=lambda: self.provider_execution_service.execute(
                    "hunter",
                    "search_domain_contacts",
                    client.search_domain_contacts,
                    domain,
                    cost=1,
                ),
            )
        except (ProviderExecutionBlockedError, ProviderExecutionError, ValueError):
            if domain:
                self._failed_hunter_lead_domains.add(domain)
            return []

        return self._map_hunter_people(company, payload)

    def generate_leads(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self.ctx.flags.get("no_enrichment"):
            self.ctx.metrics["lead_generation_skipped_no_enrichment"] = True
            return []

        leads: List[Dict[str, Any]] = []

        def _has_real_enrichment(company: Dict[str, Any]) -> bool:
            return bool(
                (company.get("enrichment_source") == "apollo")
                or (company.get("linkedin_company_url"))
                or (company.get("industry"))
                or (company.get("employee_range"))
            )

        def _should_require_enrichment(companies: List[Dict[str, Any]]) -> bool:
            # Solo exigimos enrichment si al menos UNA empresa ya viene enriquecida
            return any(_has_real_enrichment(c) for c in companies)

        require_enrichment = _should_require_enrichment(companies)
        self.ctx.metrics["lead_generation_require_enrichment"] = require_enrichment

        base_eligible_indexes = [
            idx for idx, company in enumerate(companies)
            if self._should_attempt_lead_generation(company)
        ]

        eligible_indexes = [
            idx for idx in base_eligible_indexes
            if (not require_enrichment or _has_real_enrichment(companies[idx]))
        ]
        eligible_indexes.sort(key=lambda idx: self._priority(companies[idx]), reverse=True)
        selected_indexes = set(eligible_indexes[: self.max_companies_per_run])

        self.ctx.metrics["lead_generation_candidates_total"] = len(eligible_indexes)
        self.ctx.metrics["lead_generation_selected_total"] = len(selected_indexes)
        self.ctx.metrics["lead_generation_skipped_limit"] = max(len(eligible_indexes) - len(selected_indexes), 0)
        self.ctx.metrics["lead_generation_skipped_missing_enrichment"] = max(
            len(base_eligible_indexes) - len(eligible_indexes),
            0,
        )

        for idx, company in enumerate(companies):
            if idx not in selected_indexes:
                continue

            apollo_leads = self._search_apollo_people(company)

            should_attempt_hunter = (
                not apollo_leads
                or len(apollo_leads) < self.max_leads_per_company
                or not self._apollo_has_strong_contact_signal(apollo_leads)
            )

            hunter_leads: List[Dict[str, Any]] = []
            if should_attempt_hunter:
                hunter_leads = self._search_hunter_fallback(company)

            company_leads = self._combine_company_leads(apollo_leads, hunter_leads)
            if company_leads:
                leads.extend(company_leads)
                continue

            company_key = company.get("company_key")
            domain = (company.get("resolved_domain") or "").strip().lower()
            if (
                self.enable_stub_leads
                and company_key
                and domain
                and not is_job_board_domain(domain)
                and domain not in self._failed_apollo_lead_domains
                and domain not in self._failed_hunter_lead_domains
            ):
                leads.append(
                    {
                        "company_key": company_key,
                        "contact_name": "",
                        "contact_title": "Engineering Leadership",
                        "email": f"engineering@{domain}",
                        "linkedin_url": "",
                        "lead_source": "stub_generation",
                        "lead_confidence": 0.2,
                        "email_quality_score": 0,
                        "lead_capture_reason": "stub_generation_disabled_quality",
                    }
                )

        leads = self._dedupe_leads(leads)
        self.ctx.metrics["leads_generated"] = len(leads)
        return leads
