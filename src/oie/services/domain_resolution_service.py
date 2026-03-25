from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from oie.orchestration.run_context import RunContext
from oie.services.domain_confidence_service import DomainConfidenceService
from oie.services.provider_control_service import ProviderControlService
from oie.services.serpapi_search_service import SerpAPISearchService
from oie.utils.domain_filters import is_job_board_domain, normalize_domain


BLOCKED_DOMAINS = {
    "linkedin.com",
    "www.linkedin.com",
    "lnkd.in",
    "indeed.com",
    "www.indeed.com",
    "glassdoor.com",
    "www.glassdoor.com",
    "ziprecruiter.com",
    "www.ziprecruiter.com",
    "greenhouse.io",
    "boards.greenhouse.io",
    "lever.co",
    "jobs.lever.co",
    "workable.com",
    "apply.workable.com",
    "teamtailor.com",
    "jobs.teamtailor.com",
    "breezy.hr",
    "app.breezy.hr",
    "t.co",
    "bit.ly",
    "goo.gl",
    "google.com",
    "www.google.com",
}


class DomainResolutionService:
    def __init__(
        self,
        ctx: RunContext,
        provider_control_service: Optional[ProviderControlService] = None,
        serpapi_search_service: Optional[SerpAPISearchService] = None,
    ) -> None:
        self.ctx = ctx
        self.provider_control_service = provider_control_service
        self.serpapi_search_service = serpapi_search_service

        config = ctx.config.get("domain_resolution", {}) if ctx.config else {}
        self.serpapi_fallback_limit = int(config.get("serpapi_fallback_limit", 25))
        self.review_threshold = float(config.get("review_threshold", 0.45))
        self.auto_accept_threshold = float(config.get("auto_accept_threshold", 0.80))
        self._serpapi_fallback_count = 0

        self.confidence_service = DomainConfidenceService(
            auto_accept_threshold=self.auto_accept_threshold,
            review_threshold=self.review_threshold,
        )

    def _extract_domain(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None

        value = url.strip()
        if not value:
            return None

        if "://" not in value:
            value = f"https://{value}"

        try:
            parsed = urlparse(value)
            domain = normalize_domain(parsed.netloc or "")
            return domain or None
        except Exception:
            return None

    def _is_blocked_domain(self, domain: Optional[str]) -> bool:
        if not domain:
            return True
        if domain in BLOCKED_DOMAINS:
            return True
        if is_job_board_domain(domain):
            return True
        return False

    def _should_skip_generic_name(self, company_name: Optional[str]) -> bool:
        return self.confidence_service.is_generic_company_name(company_name)

    def _build_direct_candidates(self, company: Dict[str, Any]) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []

        for source_field, url in [
            ("apply_url", company.get("apply_url")),
            ("url", company.get("url")),
        ]:
            domain = self._extract_domain(url)
            if not domain:
                continue

            candidates.append(
                {
                    "domain": domain,
                    "source": source_field,
                    "serp_rank": None,
                    "title": "",
                    "snippet": "",
                }
            )

        return candidates

    def _classify_resolution_priority(self, company: Dict[str, Any]) -> int:
        company_name = company.get("company_display") or company.get("company") or ""
        company_name_norm = str(company_name).strip().lower()

        high_priority_names = {
            "decskill españa",
            "congelados polar",
            "sofka technologies",
            "digital solutions 324 sl",
            "digital solutions 324",
            "digital solutions 324 sl.",
        }

        if company_name_norm in high_priority_names:
            return 0

        apply_domain = self._extract_domain(company.get("apply_url"))
        url_domain = self._extract_domain(company.get("url"))

        if apply_domain and self._is_blocked_domain(apply_domain):
            return 1

        if url_domain and self._is_blocked_domain(url_domain):
            return 1

        return 2


    def _resolve_domain_via_serpapi(self, company_name: Optional[str]) -> List[Dict[str, Any]]:
        if not company_name:
            return []

        if self._serpapi_fallback_count >= self.serpapi_fallback_limit:
            self.ctx.metrics["serpapi_domain_resolution_skipped_limit"] = True
            return []

        if self._should_skip_generic_name(company_name):
            self.ctx.metrics["serpapi_domain_resolution_skipped_generic_name"] = (
                int(self.ctx.metrics.get("serpapi_domain_resolution_skipped_generic_name", 0)) + 1
            )
            return []

        service = self.serpapi_search_service
        if service is None and self.provider_control_service is not None:
            service = SerpAPISearchService(self.ctx, self.provider_control_service)

        if service is None:
            self.ctx.metrics["serpapi_domain_resolution_skipped_no_service"] = True
            return []

        payload = service.search_google(f"{company_name} official website", num=5) or {}
        self._serpapi_fallback_count += 1

        organic_results = payload.get("organic_results") or []
        candidates: List[Dict[str, Any]] = []

        for idx, item in enumerate(organic_results, start=1):
            link = item.get("link") or ""
            domain = self._extract_domain(link)
            if not domain:
                continue

            candidates.append(
                {
                    "domain": domain,
                    "source": "serpapi_fallback",
                    "serp_rank": idx,
                    "title": item.get("title") or "",
                    "snippet": item.get("snippet") or "",
                }
            )

        return candidates

    def _empty_outcome(self) -> Dict[str, Any]:
        return {
            "domain": None,
            "source": None,
            "score": 0.0,
            "candidate": None,
            "validation_status": "rejected",
            "review_required": False,
            "ai_validated": 0,
        }

    def _evaluate_best_candidate(
        self,
        company_name: Optional[str],
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not candidates:
            return self._empty_outcome()

        best = self.confidence_service.pick_best_candidate(company_name, candidates)
        if not best:
            return self._empty_outcome()

        domain = best.get("domain")
        source = best.get("source")
        score = float(best.get("score", 0.0))
        blocked = bool(best.get("confidence_blocked", False))
        validation_status = best.get("validation_status", "rejected")
        review_required = bool(best.get("review_required", False))

        if blocked:
            return {
                "domain": None,
                "source": source,
                "score": 0.0,
                "candidate": domain,
                "validation_status": "rejected",
                "review_required": False,
                "ai_validated": 0,
            }

        return {
            "domain": domain if validation_status == "accepted" else None,
            "source": source,
            "score": score,
            "candidate": domain,
            "validation_status": validation_status,
            "review_required": review_required,
            "ai_validated": 0,
        }

    def _resolve_company_domain(self, company: Dict[str, Any]) -> Dict[str, Any]:
        company_name = company.get("company_display") or company.get("company")

        direct_candidates = self._build_direct_candidates(company)
        best_direct = self._evaluate_best_candidate(company_name, direct_candidates)

        if best_direct["validation_status"] == "accepted":
            return best_direct

        serp_candidates = self._resolve_domain_via_serpapi(company_name)
        best_serp = self._evaluate_best_candidate(company_name, serp_candidates)

        if best_serp["validation_status"] == "accepted":
            return best_serp

        if best_serp["candidate"]:
            if best_serp["validation_status"] == "rejected":
                self.ctx.metrics["serpapi_domain_resolution_rejected_low_confidence"] = (
                    int(self.ctx.metrics.get("serpapi_domain_resolution_rejected_low_confidence", 0)) + 1
                )
            return best_serp

        return best_direct if best_direct["candidate"] else self._empty_outcome()

    def resolve_domains(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        resolved: List[Dict[str, Any]] = []
        resolved_count = 0
        accepted_count = 0
        review_count = 0
        rejected_count = 0

        indexed_companies = list(enumerate(companies))

        urgent: List[tuple[int, Dict[str, Any]]] = []
        medium: List[tuple[int, Dict[str, Any]]] = []
        normal: List[tuple[int, Dict[str, Any]]] = []

        for item in indexed_companies:
            priority = self._classify_resolution_priority(item[1])
            if priority == 0:
                urgent.append(item)
            elif priority == 1:
                medium.append(item)
            else:
                normal.append(item)

        ordered_results: Dict[int, Dict[str, Any]] = {}

        for bucket in (urgent, medium, normal):
            for idx, company in bucket:
                outcome = self._resolve_company_domain(company)

                domain = outcome.get("domain")
                source_field = outcome.get("source")
                confidence = float(outcome.get("score", 0.0))
                candidate = outcome.get("candidate")
                validation_status = outcome.get("validation_status", "rejected")
                review_required = bool(outcome.get("review_required", False))
                ai_validated = int(outcome.get("ai_validated", 0))

                record = dict(company)
                record["resolved_domain"] = domain
                record["domain_source"] = source_field
                record["domain_confidence"] = confidence
                record["domain_candidate"] = candidate
                record["domain_validation_status"] = validation_status
                record["domain_review_required"] = 1 if review_required else 0
                record["domain_ai_validated"] = ai_validated

                if validation_status == "accepted":
                    accepted_count += 1
                elif validation_status == "review":
                    review_count += 1
                else:
                    rejected_count += 1

                if domain:
                    resolved_count += 1

                ordered_results[idx] = record

        for idx in range(len(companies)):
            resolved.append(ordered_results[idx])

        self.ctx.metrics["companies_with_domain"] = resolved_count
        self.ctx.metrics["domain_resolution_accepted"] = accepted_count
        self.ctx.metrics["domain_resolution_review"] = review_count
        self.ctx.metrics["domain_resolution_rejected"] = rejected_count
        self.ctx.metrics["domain_resolution_completed"] = True
        return resolved
