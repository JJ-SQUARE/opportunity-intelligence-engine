from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from oie.orchestration.run_context import RunContext
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
}


class DomainResolutionService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

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
            domain = (parsed.netloc or "").lower().strip()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain or None
        except Exception:
            return None

    def _is_blocked_domain(self, domain: Optional[str]) -> bool:
        if not domain:
            return True
        if domain in BLOCKED_DOMAINS:
            return True
        return False

    def _resolve_company_domain(self, company: Dict[str, Any]) -> tuple[Optional[str], Optional[str], float]:
        candidate_urls = [
            ("apply_url", company.get("apply_url")),
            ("job_url", company.get("job_url")),
            ("url", company.get("url")),
        ]

        for source_field, url in candidate_urls:
            domain = self._extract_domain(url)
            if domain and not self._is_blocked_domain(domain):
                return domain, source_field, 0.9 if source_field == "apply_url" else 0.7

        return None, None, 0.0

    def resolve_domains(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        resolved: List[Dict[str, Any]] = []
        resolved_count = 0

        for company in companies:
            domain, source_field, confidence = self._resolve_company_domain(company)

            record = dict(company)
            record["resolved_domain"] = domain
            record["domain_source"] = source_field
            record["domain_confidence"] = confidence

            if domain:
                resolved_count += 1

            resolved.append(record)

        self.ctx.metrics["companies_with_domain"] = resolved_count
        self.ctx.metrics["domain_resolution_completed"] = True

        return resolved
