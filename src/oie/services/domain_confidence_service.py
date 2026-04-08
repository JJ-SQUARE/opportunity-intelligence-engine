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
    "technology",
    "technologies",
    "tech",
    "holding",
    "holdings",
    "company",
    "companies",
    "corp",
    "corporation",
    "inc",
    "llc",
    "ltd",
    "sas",
    "sa",
    "de",
    "del",
    "la",
    "el",
    "and",
    "the",
    "españa",
    "mexico",
    "méxico",
    "colombia",
    "ecuador",
    "peru",
    "perú",
    "latam",
}


class DomainConfidenceService:
    def __init__(
        self,
        auto_accept_threshold: float = 0.80,
        review_threshold: float = 0.45,
    ) -> None:
        self.auto_accept_threshold = auto_accept_threshold
        self.review_threshold = review_threshold

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
            .replace("(", " ")
            .replace(")", " ")
            .replace("&", " ")
            .strip()
        )

    def _company_tokens(self, company_name: Optional[str]) -> List[str]:
        text = self._normalize_text(company_name)
        return [t for t in text.split() if t and len(t) > 2]

    def _extract_core_tokens(self, company_name: Optional[str]) -> List[str]:
        tokens = self._company_tokens(company_name)
        return [t for t in tokens if t not in GENERIC_COMPANY_TOKENS and len(t) > 2]

    def is_generic_company_name(self, company_name: Optional[str]) -> bool:
        return len(self._extract_core_tokens(company_name)) == 0

    def _is_blocked_domain(self, domain: Optional[str]) -> bool:
        if not domain:
            return True
        d = normalize_domain(domain)
        if not d:
            return True
        return d in BLOCKED_DOMAINS or is_job_board_domain(d)

    def _domain_brand_match_details(self, company_name: Optional[str], domain: Optional[str]) -> Dict[str, Any]:
        normalized_domain = normalize_domain(domain or "")
        domain_text = normalized_domain.replace(".", " ")
        domain_compact = normalized_domain.replace(".", "")

        tokens = self._company_tokens(company_name)
        core_tokens = self._extract_core_tokens(company_name)

        joined_all = "".join(tokens)
        joined_core = "".join(core_tokens)

        full_join_match = bool(joined_all and joined_all in domain_compact)
        core_join_match = bool(joined_core and joined_core in domain_compact)

        token_hits = sum(1 for token in tokens if token in domain_text or token in domain_compact)
        core_hits = sum(1 for token in core_tokens if token in domain_text or token in domain_compact)

        # NUEVO: match fuerte por token principal de marca
        primary_core_token = core_tokens[0] if core_tokens else ""
        primary_token_match = bool(primary_core_token and primary_core_token in domain_compact)

        brand_match = full_join_match or core_join_match or primary_token_match or core_hits > 0

        return {
            "brand_match": brand_match,
            "token_hits": token_hits,
            "core_hits": core_hits,
            "full_join_match": full_join_match,
            "core_join_match": core_join_match,
            "primary_token_match": primary_token_match,
            "primary_core_token": primary_core_token,
            "core_tokens": core_tokens,
        }

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
        subdomain_parts = normalized_domain.split(".")[:-2] if normalized_domain.count(".") >= 2 else []
        suspicious_subdomain_tokens = {"beta", "staging", "stage", "dev", "test", "qa", "uat", "sandbox", "preview"}
        suspicious_subdomain = any(part in suspicious_subdomain_tokens for part in subdomain_parts)
        generic_name = self.is_generic_company_name(company_name)
        brand_info = self._domain_brand_match_details(company_name, normalized_domain)

        brand_match = brand_info["brand_match"]
        token_hits = brand_info["token_hits"]
        core_hits = brand_info["core_hits"]
        full_join_match = brand_info["full_join_match"]
        core_join_match = brand_info["core_join_match"]
        primary_token_match = brand_info["primary_token_match"]

        reasons: List[str] = []
        raw_score = 0.0

        if blocked:
            raw_score -= 1.0
            reasons.append("blocked_domain")

        if source == "apply_url":
            raw_score += 0.55
            reasons.append("source_apply_url")
        elif source == "url":
            raw_score += 0.50
            reasons.append("source_url")
        elif source == "serpapi_fallback":
            raw_score += 0.20
            reasons.append("source_serpapi_fallback")

        if isinstance(serp_rank, int) and serp_rank > 0:
            rank_bonus = max(0.0, 0.20 - ((serp_rank - 1) * 0.03))
            raw_score += rank_bonus
            reasons.append(f"serp_rank_{serp_rank}")

        if full_join_match:
            raw_score += 0.40
            reasons.append("full_join_match")
        elif core_join_match:
            raw_score += 0.36
            reasons.append("core_join_match")
        elif primary_token_match:
            raw_score += 0.28
            reasons.append("primary_token_match")

        if core_hits >= 2:
            raw_score += 0.35
            reasons.append("core_hits_2plus")
        elif core_hits == 1:
            raw_score += 0.25
            reasons.append("core_hits_1")

        if token_hits >= 2:
            raw_score += 0.10
            reasons.append("token_hits_2plus")
        elif token_hits == 1:
            raw_score += 0.05
            reasons.append("token_hits_1")

        if generic_name:
            raw_score -= 0.10
            reasons.append("generic_company_name")

        if normalized_domain.endswith(".gov"):
            raw_score -= 0.20
            reasons.append("gov_domain_penalty")

        if normalized_domain.endswith(".edu"):
            raw_score -= 0.20
            reasons.append("edu_domain_penalty")

        if suspicious_subdomain:
            raw_score -= 0.35
            reasons.append("suspicious_subdomain_penalty")

        text = f"{title} {snippet}".strip()
        core_tokens = brand_info["core_tokens"]
        if core_tokens and text:
            text_core_hits = sum(1 for token in core_tokens if token in text)
            if text_core_hits >= 2:
                raw_score += 0.15
                reasons.append("text_core_hits_2plus")
            elif text_core_hits == 1:
                raw_score += 0.08
                reasons.append("text_core_hits_1")

        if not blocked and source in {"apply_url", "url"} and brand_match:
            raw_score = max(raw_score, 0.80)
            reasons.append("direct_url_brand_floor")

        if not blocked and not suspicious_subdomain and source == "serpapi_fallback" and full_join_match:
            raw_score = max(raw_score, 0.90)
            reasons.append("serp_brand_floor_full")
        elif not blocked and not suspicious_subdomain and source == "serpapi_fallback" and core_hits >= 1 and "official" in text:
            raw_score = max(raw_score, 0.85)
            reasons.append("serp_brand_floor_official")

        # NUEVO: match honesto por marca principal -> mínimo review
        if (
            not blocked
            and source == "serpapi_fallback"
            and not generic_name
            and (core_hits >= 1 or primary_token_match or core_join_match)
        ):
            review_floor = self.review_threshold + (0.05 if suspicious_subdomain else 0.0)
            raw_score = max(raw_score, review_floor)
            reasons.append("serp_honest_brand_review_floor")

        score = max(0.0, min(1.0, round(raw_score, 4)))

        if blocked:
            validation_status = "rejected"
        elif suspicious_subdomain and score >= self.review_threshold:
            validation_status = "review"
            reasons.append("suspicious_subdomain_forced_review")
        elif score >= self.auto_accept_threshold:
            validation_status = "accepted"
        elif score >= self.review_threshold:
            validation_status = "review"
        elif brand_match:
            validation_status = "review"
            reasons.append("brand_match_forced_review")
        else:
            validation_status = "rejected"

        review_required = validation_status == "review"
        auto_accepted = validation_status == "accepted"

        result = dict(candidate)
        result["domain"] = normalized_domain
        result["score"] = score
        result["confidence_score"] = score
        result["confidence_blocked"] = blocked
        result["confidence_brand_match"] = brand_match
        result["confidence_generic_company_name"] = generic_name
        result["confidence_reasons"] = reasons
        result["review_required"] = review_required
        result["auto_accepted"] = auto_accepted
        result["validation_status"] = validation_status
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
                1 if c.get("auto_accepted") else 0,
                0 if c.get("confidence_blocked") else 1,
            ),
            reverse=True,
        )
        return pool[0]
