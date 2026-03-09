from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import (
    ProviderExecutionBlockedError,
    ProviderExecutionError,
    ProviderExecutionService,
)


TARGET_TITLES = [
    "CTO",
    "VP Engineering",
    "Head of Engineering",
    "Engineering Director",
    "Head of Product",
]

EXCLUDED_TITLE_TERMS = [
    "recruiter",
    "talent",
    "hr",
    "human resources",
    "talent acquisition",
]


class LeadGenerationService:
    def __init__(
        self,
        ctx: RunContext,
        provider_control_service: ProviderControlService,
    ) -> None:
        self.ctx = ctx
        self.provider_control_service = provider_control_service
        self.provider_execution_service = ProviderExecutionService(ctx, provider_control_service)

    def _is_relevant_title(self, title: str) -> bool:
        value = (title or "").strip().lower()
        if not value:
            return False

        for excluded in EXCLUDED_TITLE_TERMS:
            if excluded in value:
                return False

        return True

    def _map_apollo_people(self, company_key: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        people = payload.get("people") or payload.get("contacts") or []
        leads: List[Dict[str, Any]] = []

        for person in people:
            title = person.get("title") or ""
            if not self._is_relevant_title(title):
                continue

            leads.append(
                {
                    "company_key": company_key,
                    "contact_name": person.get("name") or "",
                    "contact_title": title,
                    "email": person.get("email") or "",
                    "linkedin_url": person.get("linkedin_url") or person.get("linkedin") or "",
                    "lead_source": "apollo_people",
                    "lead_confidence": 0.9,
                }
            )

        return leads

    def _map_hunter_people(self, company_key: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        data = payload.get("data") or {}
        emails = data.get("emails") or []

        leads: List[Dict[str, Any]] = []
        for item in emails:
            title = item.get("position") or ""
            if title and not self._is_relevant_title(title):
                continue

            leads.append(
                {
                    "company_key": company_key,
                    "contact_name": item.get("first_name") or item.get("value") or "",
                    "contact_title": title or "Unknown",
                    "email": item.get("value") or "",
                    "linkedin_url": item.get("linkedin") or "",
                    "lead_source": "hunter_domain_search",
                    "lead_confidence": 0.5,
                }
            )

        return leads

    def _search_apollo_people(self, company: Dict[str, Any]) -> List[Dict[str, Any]]:
        client = self.provider_control_service.registry.get_client("apollo")
        if client is None:
            return []

        domain = company.get("resolved_domain") or ""
        company_key = company.get("company_key") or ""
        if not domain or not company_key:
            return []

        try:
            payload = self.provider_execution_service.execute(
                "apollo",
                "search_people_by_domain_and_titles",
                client.search_people_by_domain_and_titles,
                domain,
                TARGET_TITLES,
                cost=1,
            )
        except (ProviderExecutionBlockedError, ProviderExecutionError, ValueError):
            return []

        return self._map_apollo_people(company_key, payload)

    def _search_hunter_fallback(self, company: Dict[str, Any]) -> List[Dict[str, Any]]:
        client = self.provider_control_service.registry.get_client("hunter")
        if client is None:
            return []

        domain = company.get("resolved_domain") or ""
        company_key = company.get("company_key") or ""
        if not domain or not company_key:
            return []

        try:
            payload = self.provider_execution_service.execute(
                "hunter",
                "search_domain_contacts",
                client.search_domain_contacts,
                domain,
                cost=1,
            )
        except (ProviderExecutionBlockedError, ProviderExecutionError, ValueError):
            return []

        return self._map_hunter_people(company_key, payload)

    def generate_leads(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self.ctx.flags.get("no_enrichment"):
            self.ctx.metrics["lead_generation_skipped_no_enrichment"] = True
            return []

        leads: List[Dict[str, Any]] = []

        for company in companies:
            apollo_leads = self._search_apollo_people(company)
            if apollo_leads:
                leads.extend(apollo_leads)
                continue

            hunter_leads = self._search_hunter_fallback(company)
            if hunter_leads:
                leads.extend(hunter_leads)
                continue

            company_key = company.get("company_key")
            domain = company.get("resolved_domain") or ""
            if company_key and domain:
                leads.append(
                    {
                        "company_key": company_key,
                        "contact_name": "",
                        "contact_title": "Engineering Leadership",
                        "email": f"engineering@{domain}",
                        "linkedin_url": "",
                        "lead_source": "stub_generation",
                        "lead_confidence": 0.2,
                    }
                )

        self.ctx.metrics["leads_generated"] = len(leads)
        return leads
