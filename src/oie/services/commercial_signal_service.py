from __future__ import annotations

from typing import Any, Dict

from oie.utils.domain_filters import is_job_board_domain, normalize_domain


class CommercialSignalService:
    COMPANY_TYPE_ALIASES = {
        "product_company": "end_client",
        "staffing_agency": "staffing",
        "outsourcing": "consulting",
    }

    NON_ICP_TYPES = {"staffing", "consulting", "marketplace", "job_board", "competitor"}

    VENDOR_COMPETITOR_HINTS = {
        "babel group",
        "bairesdev",
        "globant",
        "michael page",
        "pagegroup",
        "reclutamiento especializado",
        "softserve",
        "softtek",
        "staff augmentation",
        "staffing",
        "technology consulting",
    }

    ATS_HOST_HINTS = (
        "greenhouse.io",
        "greenhouse.com",
        "lever.co",
        "jobs.ashbyhq.com",
        "ashbyhq.com",
        "workable.com",
        "smartrecruiters.com",
        "myworkdayjobs.com",
        "workday.com",
        "breezy.hr",
        "recruitee.com",
        "teamtailor.com",
        "jobvite.com",
        "applytojob.com",
        "boards.greenhouse.io",
        "jobs.lever.co",
    )

    NON_COMMERCIAL_DOMAIN_SUFFIXES = (
        ".example",
        ".invalid",
        ".test",
        ".localhost",
    )

    @staticmethod
    def safe_text(value: Any) -> str:
        return " ".join(str(value or "").split()).strip()

    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value if value is not None else default)
        except Exception:
            return default

    @staticmethod
    def safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(value if value is not None else default)
        except Exception:
            return default

    def normalized_company_type(self, value: Any) -> str:
        raw = self.safe_text(value).lower()
        return self.COMPANY_TYPE_ALIASES.get(raw, raw)

    def is_benchmark_competitor(self, row: Dict[str, Any]) -> bool:
        return self.normalized_company_type(row.get("company_type_ai")) == "competitor"

    def _normalized_domain(self, domain: Any) -> str:
        return normalize_domain(self.safe_text(domain))

    def _domain_is_commercially_usable(self, domain: Any) -> bool:
        value = self._normalized_domain(domain)
        if not value:
            return False
        if is_job_board_domain(value):
            return False
        if any(value.endswith(suffix) for suffix in self.NON_COMMERCIAL_DOMAIN_SUFFIXES):
            return False
        return not any(hint in value for hint in self.ATS_HOST_HINTS)

    def has_usable_company_domain(self, row: Dict[str, Any]) -> bool:
        validation_status = self.safe_text(row.get("domain_validation_status")).lower()
        resolved_domain = row.get("resolved_domain")
        return validation_status in {"accepted", "accepted_ai_validated"} and self._domain_is_commercially_usable(resolved_domain)

    def has_contact_email(self, row: Dict[str, Any]) -> bool:
        best_contact_email = self.safe_text(
            row.get("best_contact_email") or row.get("email")
        )
        return bool(best_contact_email)

    def has_contact_linkedin(self, row: Dict[str, Any]) -> bool:
        best_contact_linkedin_url = self.safe_text(
            row.get("best_contact_linkedin_url") or row.get("linkedin_url")
        )
        return bool(best_contact_linkedin_url)

    def has_contact_channel(self, row: Dict[str, Any]) -> bool:
        return bool(self.has_contact_email(row) or self.has_contact_linkedin(row))

    def has_company_linkedin(self, row: Dict[str, Any]) -> bool:
        linkedin_company_url = self.safe_text(row.get("linkedin_company_url"))
        return bool(linkedin_company_url)

    def has_company_channel(self, row: Dict[str, Any]) -> bool:
        return bool(self.has_usable_company_domain(row) or self.has_company_linkedin(row))

    def has_real_reachability_signal(self, row: Dict[str, Any]) -> bool:
        return self.has_contact_channel(row)

    def has_soft_reachability_signal(self, row: Dict[str, Any]) -> bool:
        enrichment_source = self.safe_text(row.get("enrichment_source")).lower()
        return bool(
            self.has_company_channel(row)
            or enrichment_source == "apollo"
        )

    def has_reachability_signal(self, row: Dict[str, Any]) -> bool:
        return self.has_real_reachability_signal(row)

    def _has_real_icp_signal(self, row: Dict[str, Any]) -> bool:
        has_real_icp = row.get("has_real_icp")
        if isinstance(has_real_icp, bool):
            return has_real_icp
        if str(has_real_icp).strip().lower() in {"1", "true", "yes"}:
            return True

        company_type = self.normalized_company_type(row.get("company_type_ai"))
        icp_fit_bucket = self.safe_text(row.get("icp_fit_bucket")).lower()
        score_icp_fit = self.safe_float(row.get("score_icp_fit"))
        score_pain_urgency = self.safe_float(row.get("score_pain_urgency"))
        opportunity_score = self.safe_float(row.get("opportunity_score"))

        if icp_fit_bucket == "strong":
            return True
        if score_icp_fit >= 16:
            return True
        if company_type == "end_client" and score_pain_urgency >= 12:
            return True
        if score_icp_fit >= 12 and opportunity_score >= 55:
            return True
        if company_type == "end_client" and opportunity_score >= 55:
            return True
        return False

    def _has_minimum_job_signal(self, row: Dict[str, Any]) -> bool:
        jobs_count = self.safe_int(row.get("jobs_count"), self.safe_int(row.get("total_openings")))
        score_openings = self.safe_float(row.get("score_openings"))
        score_pain_urgency = self.safe_float(row.get("score_pain_urgency"))
        score_role_seniority_mix = self.safe_float(row.get("score_role_seniority_mix"))
        return bool(
            jobs_count >= 1
            or score_openings >= 4
            or score_pain_urgency >= 8
            or score_role_seniority_mix >= 7
        )

    def _is_investigable_unknown_candidate(self, row: Dict[str, Any]) -> bool:
        company_type = self.normalized_company_type(row.get("company_type_ai"))
        if company_type not in {"", "unknown"}:
            return False
        if self._is_vendor_like_or_competitor(row):
            return False

        opportunity_score = self.safe_float(row.get("opportunity_score"))
        score_icp_fit = self.safe_float(row.get("score_icp_fit"))
        score_pain_urgency = self.safe_float(row.get("score_pain_urgency"))

        has_meaningful_score = (
            opportunity_score >= 30
            or score_icp_fit >= 12
            or (score_pain_urgency >= 12 and opportunity_score >= 35)
        )

        return bool(
            has_meaningful_score
            and self._has_minimum_job_signal(row)
            and (
                self.has_real_reachability_signal(row)
                or self.has_soft_reachability_signal(row)
            )
            and (
                self.has_usable_company_domain(row)
                or self.has_company_linkedin(row)
                or self.safe_text(row.get("enrichment_source")).lower() == "apollo"
            )
        )

    def is_unknown_weak(self, row: Dict[str, Any]) -> bool:
        company_type = self.normalized_company_type(row.get("company_type_ai"))
        if company_type not in {"", "unknown"}:
            return False
        return not (
            (
                self._has_real_icp_signal(row)
                or self._is_investigable_unknown_candidate(row)
            )
            and self._has_minimum_job_signal(row)
            and (
                self.has_real_reachability_signal(row)
                or self._is_investigable_unknown_candidate(row)
            )
        )

    def _is_vendor_like_or_competitor(self, row: Dict[str, Any]) -> bool:
        company_type = self.normalized_company_type(row.get("company_type_ai"))
        competitor_penalty = self.safe_float(row.get("score_penalty_competitor"))
        haystack = " ".join(
            [
                self.safe_text(row.get("company_display")),
                self.safe_text(row.get("company")),
                self.safe_text(row.get("company_description")),
                self.safe_text(row.get("industry")),
                self.safe_text(row.get("resolved_domain")),
                self.safe_text(row.get("linkedin_company_url")),
            ]
        ).lower()

        return bool(
            company_type in self.NON_ICP_TYPES
            or competitor_penalty <= -20
            or any(hint in haystack for hint in self.VENDOR_COMPETITOR_HINTS)
        )

    def is_commercially_actionable(self, row: Dict[str, Any]) -> bool:
        company_type = self.normalized_company_type(row.get("company_type_ai"))
        opportunity_score = self.safe_float(row.get("opportunity_score"))

        if self._is_vendor_like_or_competitor(row):
            return False
        if self.is_unknown_weak(row):
            return False

        has_real_icp = self._has_real_icp_signal(row)
        has_job_signal = self._has_minimum_job_signal(row)
        has_reachability = self.has_soft_reachability_signal(row)

        if not has_reachability and not (
            company_type in {"", "unknown"}
            and self._is_investigable_unknown_candidate(row)
        ):
            return False

        if company_type == "end_client":
            return bool(
                has_reachability
                and (
                    has_real_icp
                    or opportunity_score >= 40
                    or self.safe_float(row.get("score_icp_fit")) >= 12
                )
            )

        if company_type in {"", "unknown"}:
            return bool(
                has_job_signal
                and has_reachability
                and (
                    has_real_icp
                    or self._is_investigable_unknown_candidate(row)
                )
            )

        return has_real_icp and has_job_signal

    def derived_suggested_outreach_channel(self, row: Dict[str, Any]) -> str:
        if self.has_contact_email(row):
            return "email"
        if self.has_contact_linkedin(row):
            return "linkedin"
        if self.has_company_linkedin(row):
            return "company_linkedin"
        if self.has_usable_company_domain(row):
            return "website_only"
        return "no_channel"

    def derived_icp_bucket(self, row: Dict[str, Any]) -> str:
        company_type = self.normalized_company_type(row.get("company_type_ai"))
        opportunity_score = self.safe_float(row.get("opportunity_score"))
        has_real_icp = self._has_real_icp_signal(row)
        has_job_signal = self._has_minimum_job_signal(row)

        if self.is_benchmark_competitor(row):
            return "benchmark_competitor"
        if company_type in self.NON_ICP_TYPES:
            return "non_icp"
        if company_type == "end_client" and opportunity_score >= 55:
            return "strong_icp"
        if has_real_icp:
            return "possible_icp"
        if company_type == "end_client" and opportunity_score >= 25:
            return "possible_icp"
        if company_type in {"", "unknown"} and self._is_investigable_unknown_candidate(row):
            return "possible_icp"
        if company_type in {"", "unknown"} and opportunity_score >= 40 and has_job_signal and self.has_reachability_signal(row):
            return "possible_icp"
        return "weak_icp"

    def derived_reachability_ready(self, row: Dict[str, Any]) -> int:
        return 1 if self.has_real_reachability_signal(row) else 0

    def derived_outreach_status(self, row: Dict[str, Any]) -> str:
        validation_status = self.safe_text(row.get("domain_validation_status")).lower()

        if self._is_vendor_like_or_competitor(row):
            return "deprioritized_competitor"
        if validation_status == "review":
            return "review_domain"
        if self.has_contact_email(row):
            return "ready_email"
        if self.has_contact_linkedin(row):
            return "ready_linkedin"
        if self.has_company_linkedin(row) or self.has_usable_company_domain(row):
            return "research_needed"
        if validation_status in {"rejected", "rejected_aggregator", "rejected_confidential", "rejected_low_confidence", "review"}:
            return "pending_domain"
        return "insufficient_data"

    def derived_commercial_bucket(self, row: Dict[str, Any]) -> str:
        company_type = self.normalized_company_type(row.get("company_type_ai"))
        icp_bucket = self.derived_icp_bucket(row)
        has_real_icp = self._has_real_icp_signal(row)

        if self._is_vendor_like_or_competitor(row):
            return "competitor_watchlist"
        if not self.is_commercially_actionable(row):
            return "low_fit_noise"
        if icp_bucket == "strong_icp":
            return "icp_target"
        if company_type == "end_client" or has_real_icp or self._is_investigable_unknown_candidate(row):
            return "partner_candidate"
        return "low_fit_noise"

    def derived_commercial_priority_score(self, row: Dict[str, Any]) -> int:
        opportunity_score = self.safe_float(row.get("opportunity_score"))
        validation_status = self.safe_text(row.get("domain_validation_status")).lower()
        best_email_quality_score = self.safe_float(
            row.get("best_email_quality_score", row.get("email_quality_score"))
        )
        best_lead_source = self.safe_text(
            row.get("best_lead_source") or row.get("lead_source")
        ).lower()
        company_type = self.normalized_company_type(row.get("company_type_ai"))

        if not self.is_commercially_actionable(row):
            return 0

        score = opportunity_score

        if self.has_usable_company_domain(row):
            score += 8
        elif validation_status in {"accepted", "accepted_ai_validated"}:
            score -= 6

        if self.has_contact_email(row):
            score += 14
        if self.has_contact_linkedin(row):
            score += 6
        if best_email_quality_score >= 80:
            score += 5
        elif best_email_quality_score >= 50:
            score += 2

        if best_lead_source == "apollo_people":
            score += 4
        elif best_lead_source == "hunter_domain_search":
            score += 2

        if company_type == "end_client":
            score += 6
        if self.has_company_linkedin(row):
            score += 2

        if validation_status == "review":
            score -= 20
        elif validation_status not in {"", "accepted", "accepted_ai_validated"}:
            score -= 12

        
        if company_type in {"competitor", *self.NON_ICP_TYPES}:
            score -= 80
        elif self.safe_float(row.get("score_penalty_competitor")) <= -20:
            score -= 60

        return max(0, int(round(score)))

    def commercial_rank_tuple(self, row: Dict[str, Any]) -> tuple:
        finalized = self.finalize_row(row)
        commercial_bucket = self.safe_text(finalized.get("commercial_bucket")).lower()
        outreach_status = self.safe_text(finalized.get("outreach_status")).lower()

        bucket_rank = {
            "icp_target": 3,
            "partner_candidate": 2,
            "low_fit_noise": 1,
            "competitor_watchlist": 0,
        }.get(commercial_bucket, 0)

        outreach_rank = {
            "ready_email": 5,
            "ready_linkedin": 4,
            "research_needed": 3,
            "review_domain": 2,
            "pending_domain": 1,
            "insufficient_data": 0,
            "deprioritized_competitor": -1,
        }.get(outreach_status, 0)

        return (
            bucket_rank,
            self.safe_int(finalized.get("reachability_ready")),
            outreach_rank,
            self.safe_int(finalized.get("commercial_priority_score")),
            self.safe_float(finalized.get("opportunity_score")),
            self.safe_float(finalized.get("classification_confidence_ai")),
            self.safe_text(finalized.get("company_display")).lower(),
        )

    def finalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(row)
        enriched["suggested_outreach_channel"] = self.derived_suggested_outreach_channel(enriched)
        enriched["outreach_status"] = self.derived_outreach_status(enriched)
        enriched["icp_bucket"] = self.derived_icp_bucket(enriched)
        enriched["reachability_ready"] = self.derived_reachability_ready(enriched)
        enriched["real_reachability_ready"] = 1 if self.has_real_reachability_signal(enriched) else 0
        enriched["soft_reachability_ready"] = 1 if self.has_soft_reachability_signal(enriched) else 0
        enriched["commercial_bucket"] = self.derived_commercial_bucket(enriched)
        enriched["commercial_priority_score"] = self.derived_commercial_priority_score(enriched)
        enriched["commercially_actionable"] = self.is_commercially_actionable(enriched)
        enriched["company_domain_usable"] = self.has_usable_company_domain(enriched)
        enriched["commercial_domain_usable"] = self.has_usable_company_domain(enriched)
        enriched["contact_channel_ready"] = self.has_contact_channel(enriched)
        enriched["company_channel_ready"] = self.has_company_channel(enriched)
        return enriched
