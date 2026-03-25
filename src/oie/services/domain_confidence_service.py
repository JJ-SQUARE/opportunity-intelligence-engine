from __future__ import annotations

from typing import Any, Dict, List, Optional

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
    "jooble.org",
    "www.jooble.org",
    "jobrapido.com",
    "www.jobrapido.com",
    "recruit.net",
    "www.recruit.net",
    "expertini.com",
    "www.expertini.com",
    "talent.com",
    "www.talent.com",
    "whatjobs.com",
    "www.whatjobs.com",
    "computrabajo.com",
    "www.computrabajo.com",
    "elempleo.com",
    "www.elempleo.com",
    "occ.com.mx",
    "www.occ.com.mx",
    "buscojobs.com.ec",
    "www.buscojobs.com.ec",
    "mifuturoempleo.com",
    "www.mifuturoempleo.com",
    "trabajosdiarios.com",
    "www.trabajosdiarios.com",
    "bebee.com",
    "www.bebee.com",
    "jobijoba.mx",
    "www.jobijoba.mx",
}

GENERIC_COMPANY_TOKENS = {
    "join",
    "ready",
    "global",
    "group",
    "grupo",
    "solutions",
    "solution",
    "systems",
    "system",
    "digital",
    "commercial",
    "comercial",
    "services",
    "service",
    "consulting",
    "consultoria",
    "consultoría",
    "academy",
    "academia",
    "talent",
    "training",
    "confidential",
}


class DomainConfidenceService:
    def _normalize_text(self, value: Optional[str]) -> str:
        if not value:
            return ""
        return (
            value.lower()
            .replace(".", " ")
            .replace(",", " ")
            .replace("-", " ")
            .replace("_", " ")
            .replace("/", " ")
            .strip()
        )

    def _company_tokens(self, company_name: Optional[str]) -> List[str]:
        text = self._normalize_text(company_name)
        return [t for t in text.split() if t and len(t) > 2]

    def is_generic_company_name(self, company_name: Optional[str]) -> bool:
        tokens = self._company_tokens(company_name)
        if not tokens:
            return True

        meaningful = [t for t in tokens if t not in GENERIC_COMPANY_TOKENS]
        return len(meaningful) == 0

    def _is_blocked_domain(self, domain: Optional[str]) -> bool:
        if not domain:
            return True
        d = normalize_domain(domain)
        if not d:
            return True
        return d in BLOCKED_DOMAINS or is_job_board_domain(d)

    def _domain_brand_match(self, company_name: Optional[str], domain: Optional[str]) -> bool:
        if not company_name or not domain:
            return False

        tokens = self._company_tokens(company_name)
        if not tokens:
            return False

        normalized_domain = normalize_domain(domain)
        domain_text = normalized_domain.replace(".", " ")
        domain_compact = normalized_domain.replace(".", "")

        joined = "".join(tokens)
        if joined and joined in domain_compact:
            return True

        hits = sum(1 for token in tokens if token in domain_text or token in domain_compact)
        return hits >= max(1, min(2, len(tokens)))

    def score_candidate(
        self,
        company_name: Optional[str],
        candidate: Optional[Dict[str, Any]] = None,
        *,
        domain: Optional[str] = None,
        source: Optional[str] = None,
        serp_rank: Optional[int] = None,
        title: Optional[str] = None,
        snippet: Optional[str] = None,
    ) -> Dict[str, Any]:
        if candidate is None:
            candidate = {
                "domain": domain,
                "source": source,
                "serp_rank": serp_rank,
                "title": title,
                "snippet": snippet,
            }

        normalized_domain = normalize_domain(candidate.get("domain") or "")
        source = candidate.get("source")
        serp_rank = candidate.get("serp_rank")
        title = self._normalize_text(candidate.get("title"))
        snippet = self._normalize_text(candidate.get("snippet"))

        blocked = self._is_blocked_domain(normalized_domain)
        brand_match = self._domain_brand_match(company_name, normalized_domain)
        generic_name = self.is_generic_company_name(company_name)

        reasons: List[str] = []
        raw_score = 0.0

        if blocked:
            raw_score -= 1.0
            reasons.append("blocked_domain")

        if source == "apply_url":
            raw_score += 0.25
            reasons.append("source_apply_url")
        elif source == "url":
            raw_score += 0.20
            reasons.append("source_url")
        elif source == "serpapi_fallback":
            raw_score += 0.15
            reasons.append("source_serpapi_fallback")

        if isinstance(serp_rank, int) and serp_rank > 0:
            rank_bonus = max(0.0, 0.20 - ((serp_rank - 1) * 0.03))
            raw_score += rank_bonus
            reasons.append(f"serp_rank_{serp_rank}")

        if brand_match:
            raw_score += 0.55
            reasons.append("brand_match")

        if generic_name:
            raw_score -= 0.20
            reasons.append("generic_company_name")

        if normalized_domain.endswith(".gov"):
            raw_score -= 0.20
            reasons.append("gov_domain_penalty")

        if normalized_domain.endswith(".edu"):
            raw_score -= 0.20
            reasons.append("edu_domain_penalty")

        tokens = self._company_tokens(company_name)
        if tokens:
            text = f"{title} {snippet}"
            token_hits = sum(1 for token in tokens if token in text)
            if token_hits:
                raw_score += min(0.15, token_hits * 0.05)
                reasons.append(f"text_token_hits_{token_hits}")

        score = max(0.0, min(1.0, round(raw_score, 4)))

        result = dict(candidate)
        result["domain"] = normalized_domain
        result["score"] = score
        result["confidence_score"] = score
        result["confidence_blocked"] = blocked
        result["confidence_brand_match"] = brand_match
        result["confidence_generic_company_name"] = generic_name
        result["confidence_reasons"] = reasons
        result["review_required"] = score < 0.80
        result["auto_accepted"] = score >= 0.80
        return result

    def pick_best_candidate(
        self,
        company_name: Optional[str],
        candidates: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not candidates:
            return None

        scored = [self.score_candidate(company_name=company_name, candidate=c) for c in candidates]

        valid = [c for c in scored if not c.get("confidence_blocked")]
        pool = valid if valid else scored
        if not pool:
            return None

        pool.sort(
            key=lambda c: (
                c.get("score", 0.0),
                1 if c.get("confidence_brand_match") else 0,
                0 if c.get("confidence_blocked") else 1,
            ),
            reverse=True,
        )
        return pool[0]
