from __future__ import annotations

from typing import Any, Dict, List


SOURCE_PRIORITY = {
    "apollo_people": 3,
    "hunter_domain_search": 2,
    "stub_generation": 1,
}


class CommercialSelectionService:
    def __init__(self, commercial_signal_service: Any | None = None) -> None:
        self.commercial_signal_service = commercial_signal_service

    def safe_text(self, value: Any) -> str:
        return " ".join(str(value or "").split()).strip()

    def safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value if value is not None else default)
        except Exception:
            return default

    def safe_int(self, value: Any, default: int = 0) -> int:
        try:
            return int(value if value is not None else default)
        except Exception:
            return default

    def _finalize_company(self, company: Dict[str, Any]) -> Dict[str, Any]:
        if self.commercial_signal_service is None:
            return dict(company)
        return self.commercial_signal_service.finalize_row(company)

    def analytic_company_sort_key(self, company: Dict[str, Any]) -> tuple:
        finalized = dict(company)
        return (
            self.safe_float(finalized.get("opportunity_score")),
            self.safe_float(finalized.get("classification_confidence_ai")),
            self.safe_float(finalized.get("score_icp_fit")),
            self.safe_float(finalized.get("score_pain_urgency")),
            self.safe_float(finalized.get("score_company_type")),
            self.safe_float(finalized.get("score_openings")),
            1 if self.safe_text(finalized.get("resolved_domain")) else 0,
            1 if self.safe_text(finalized.get("linkedin_company_url")) else 0,
            self.safe_text(finalized.get("company_display")).lower(),
        )

    def company_sort_key(self, company: Dict[str, Any]) -> tuple:
        finalized = self._finalize_company(company)

        if self.commercial_signal_service is not None:
            return self.commercial_signal_service.commercial_rank_tuple(finalized)

        return self.analytic_company_sort_key(finalized)

    def sort_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        items = [self._finalize_company(company) for company in (companies or [])]
        items.sort(key=self.company_sort_key, reverse=True)
        return items

    def sort_companies_analytic(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        items = [dict(company) for company in (companies or [])]
        items.sort(key=self.analytic_company_sort_key, reverse=True)
        return items

    def commercially_actionable_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        items = self.sort_companies(companies)
        if self.commercial_signal_service is None:
            return items

        actionable = [
            company
            for company in items
            if bool(company.get("commercially_actionable"))
            and self.safe_text(company.get("commercial_bucket")).lower()
            not in {"low_fit_noise", "competitor_watchlist"}
        ]
        return actionable

    def top_companies(
        self,
        companies: List[Dict[str, Any]],
        limit: int = 10,
        include_non_actionable_fallback: bool = False,
    ) -> List[Dict[str, Any]]:
        actionable = self.commercially_actionable_companies(companies)
        if actionable:
            return actionable[:limit]

        if include_non_actionable_fallback:
            return self.sort_companies(companies)[:limit]

        return []

    def top_companies_analytic(
        self,
        companies: List[Dict[str, Any]],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        return self.sort_companies_analytic(companies)[:limit]

    def has_lead_email(self, lead: Dict[str, Any]) -> bool:
        return bool(self.safe_text(lead.get("email")))

    def has_lead_linkedin(self, lead: Dict[str, Any]) -> bool:
        return bool(self.safe_text(lead.get("linkedin_url")))

    def has_lead_channel(self, lead: Dict[str, Any]) -> bool:
        return self.has_lead_email(lead) or self.has_lead_linkedin(lead)

    def has_lead_name(self, lead: Dict[str, Any]) -> bool:
        return bool(self.safe_text(lead.get("contact_name")))

    def is_stub_lead(self, lead: Dict[str, Any]) -> bool:
        source = self.safe_text(lead.get("lead_source")).lower()
        if source == "stub_generation":
            return True
        if source == "apollo_people" and not self.has_lead_name(lead) and not self.has_lead_channel(lead):
            return True
        return False

    def is_usable_lead(
        self,
        lead: Dict[str, Any],
        require_channel: bool = True,
        min_relevance_score: int = 45,
    ) -> bool:
        company_key = self.safe_text(lead.get("company_key"))
        if not company_key:
            return False

        if self.is_stub_lead(lead):
            return False

        relevance = self.safe_float(lead.get("lead_relevance_score"))
        if relevance < float(min_relevance_score):
            return False

        if require_channel and not self.has_lead_channel(lead):
            return False

        if not self.has_lead_name(lead) and not self.has_lead_channel(lead):
            return False

        return True

    def analytic_lead_sort_key(self, lead: Dict[str, Any]) -> tuple:
        source = self.safe_text(lead.get("lead_source")).lower()
        linkedin_present = 1 if self.has_lead_linkedin(lead) else 0
        email_present = 1 if self.has_lead_email(lead) else 0
        contact_name = self.safe_text(lead.get("contact_name")).lower()

        return (
            self.safe_int(lead.get("lead_relevance_score")),
            self.safe_int(lead.get("email_quality_score")),
            self.safe_float(lead.get("lead_confidence")),
            self.safe_int(lead.get("lead_score_source")),
            SOURCE_PRIORITY.get(source, 0),
            email_present,
            linkedin_present,
            contact_name,
        )

    def lead_sort_key(self, lead: Dict[str, Any]) -> tuple:
        source = self.safe_text(lead.get("lead_source")).lower()
        has_email = 1 if self.has_lead_email(lead) else 0
        has_linkedin = 1 if self.has_lead_linkedin(lead) else 0
        has_channel = 1 if self.has_lead_channel(lead) else 0
        has_name = 1 if self.has_lead_name(lead) else 0
        is_stub = 1 if self.is_stub_lead(lead) else 0
        contact_name = self.safe_text(lead.get("contact_name")).lower()

        return (
            has_channel,
            has_email,
            has_linkedin,
            has_name,
            -is_stub,
            self.safe_int(lead.get("lead_relevance_score")),
            self.safe_int(lead.get("lead_score_source")),
            SOURCE_PRIORITY.get(source, 0),
            self.safe_int(lead.get("email_quality_score")),
            self.safe_float(lead.get("lead_confidence")),
            contact_name,
        )

    def sort_leads(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        items = [dict(lead) for lead in (leads or [])]
        items.sort(key=self.lead_sort_key, reverse=True)
        return items

    def sort_leads_analytic(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        items = [dict(lead) for lead in (leads or [])]
        items.sort(key=self.analytic_lead_sort_key, reverse=True)
        return items

    def usable_leads(
        self,
        leads: List[Dict[str, Any]],
        *,
        min_relevance_score: int = 45,
        require_channel: bool = True,
    ) -> List[Dict[str, Any]]:
        ranked = self.sort_leads(leads)
        return [
            lead
            for lead in ranked
            if self.is_usable_lead(
                lead,
                require_channel=require_channel,
                min_relevance_score=min_relevance_score,
            )
        ]

    def top_leads(
        self,
        leads: List[Dict[str, Any]],
        limit: int = 10,
        *,
        require_channel: bool = True,
        min_relevance_score: int = 45,
        include_non_usable_fallback: bool = False,
    ) -> List[Dict[str, Any]]:
        usable = self.usable_leads(
            leads,
            min_relevance_score=min_relevance_score,
            require_channel=require_channel,
        )
        if usable:
            return usable[:limit]

        if include_non_usable_fallback:
            return self.sort_leads(leads)[:limit]

        return []

    def top_leads_analytic(
        self,
        leads: List[Dict[str, Any]],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        return self.sort_leads_analytic(leads)[:limit]

    def select_best_lead(
        self,
        leads: List[Dict[str, Any]],
        *,
        require_channel: bool = True,
        min_relevance_score: int = 45,
        include_non_usable_fallback: bool = False,
    ) -> Dict[str, Any] | None:
        ranked = self.top_leads(
            leads,
            limit=1,
            require_channel=require_channel,
            min_relevance_score=min_relevance_score,
            include_non_usable_fallback=include_non_usable_fallback,
        )
        if not ranked:
            return None
        return ranked[0]

    

    def _seniority_bucket(self, lead):
        title = self.safe_text(lead.get("contact_title")).lower()

        if any(t in title for t in ["cto", "chief technology officer", "cio", "cdo"]):
            return "c_level"

        if any(t in title for t in ["vp", "vice president"]):
            return "vp"

        if any(t in title for t in ["head", "director"]):
            return "director"

        if any(t in title for t in ["manager"]):
            return "manager"

        return "other"

    def select_top_leads_per_company(
        self,
        leads: List[Dict[str, Any]],
        max_leads_per_company: int = 3,
        min_relevance_score: int = 45,
        require_channel: bool = True,
    ) -> List[Dict[str, Any]]:
        ranked = self.usable_leads(
            leads,
            min_relevance_score=min_relevance_score,
            require_channel=require_channel,
        )
        max_per_company = max(1, self.safe_int(max_leads_per_company, 3))
        selected: List[Dict[str, Any]] = []
        seen = set()
        seen_buckets_by_company: Dict[str, set] = {}
        counts_by_company: Dict[str, int] = {}

        for lead in ranked:
            company_key = self.safe_text(lead.get("company_key"))
            if not company_key:
                continue

            email = self.safe_text(lead.get("email")).lower()
            linkedin_url = self.safe_text(lead.get("linkedin_url")).lower()
            seniority_bucket = self._seniority_bucket(lead)

            dedupe_key = email or linkedin_url or (
                f"{company_key}|"
                f"{self.safe_text(lead.get('contact_name')).lower()}|"
                f"{self.safe_text(lead.get('contact_title')).lower()}"
            )
            if dedupe_key in seen:
                continue

            company_count = counts_by_company.get(company_key, 0)
            if company_count >= max_per_company:
                continue

            company_buckets = seen_buckets_by_company.setdefault(company_key, set())
            if seniority_bucket in company_buckets:
                continue

            seen.add(dedupe_key)
            company_buckets.add(seniority_bucket)
            counts_by_company[company_key] = company_count + 1
            selected.append(dict(lead))

        return selected

    def select_contacts(
        self,
        *,
        company_key: str,
        contacts: List[Dict[str, Any]],
        max_contacts: int = 3,
        min_relevance_score: int = 45,
    ) -> List[Dict[str, Any]]:
        normalized_company_key = self.safe_text(company_key)
        scoped_contacts: List[Dict[str, Any]] = []

        for contact in contacts or []:
            contact_company_key = self.safe_text(contact.get("company_key"))
            if normalized_company_key and contact_company_key not in {"", normalized_company_key}:
                continue

            enriched_contact = dict(contact)
            if normalized_company_key and not self.safe_text(enriched_contact.get("company_key")):
                enriched_contact["company_key"] = normalized_company_key
            scoped_contacts.append(enriched_contact)

        return self.select_top_leads_per_company(
            scoped_contacts,
            max_leads_per_company=max_contacts,
            min_relevance_score=min_relevance_score,
            require_channel=True,
        )

    def is_deprioritized_for_outreach(self, row: Dict[str, Any]) -> bool:
        finalized = self._finalize_company(row)
        commercial_bucket = self.safe_text(finalized.get("commercial_bucket")).lower()
        outreach_status = self.safe_text(finalized.get("outreach_status")).lower()

        return (
            commercial_bucket in {"competitor_watchlist", "low_fit_noise"}
            or outreach_status == "deprioritized_competitor"
            or not bool(finalized.get("commercially_actionable"))
        )

    def rows_for_apollo_import(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered: List[Dict[str, Any]] = []

        for row in rows or []:
            finalized = self._finalize_company(row)
            commercial_bucket = self.safe_text(finalized.get("commercial_bucket")).lower()
            if commercial_bucket != "icp_target":
                continue
            if self.is_deprioritized_for_outreach(finalized):
                continue
            if not bool(finalized.get("company_domain_usable")):
                continue
            filtered.append(finalized)

        return filtered

    def rows_with_selected_contacts(
        self,
        *,
        rows: List[Dict[str, Any]],
        contacts_by_company: Dict[str, List[Dict[str, Any]]],
        max_contacts: int = 3,
        min_relevance_score: int = 45,
    ) -> List[Dict[str, Any]]:
        filtered: List[Dict[str, Any]] = []

        for row in rows or []:
            finalized = self._finalize_company(row)
            if self.is_deprioritized_for_outreach(finalized):
                continue

            company_key = self.safe_text(finalized.get("company_key"))
            if not company_key:
                continue

            selected_contacts = self.select_contacts(
                company_key=company_key,
                contacts=contacts_by_company.get(company_key, []),
                max_contacts=max_contacts,
                min_relevance_score=min_relevance_score,
            )
            if not selected_contacts:
                continue

            filtered.append(finalized)

        return filtered
