from __future__ import annotations

import re
from typing import Any, Dict, List

from oie.providers.base import ProviderClient


AGGREGATOR_HINTS = {
    "jobgether",
    "multitrabajos",
    "vacantesdigitales",
    "computrabajo",
    "linkedin",
    "indeed",
    "glassdoor",
    "grabjobs",
    "talenteca",
    "jobleads",
    "oficinaempleo",
    "quierolaburo",
    "jooble",
    "jobrapido",
    "trabajo",
    "bumeran",
    "elempleo",
    "magneto365",
    "sercanto",
    "pangian",
    "adzuna",
    "ok.com",
}


class OpenAIAdapter(ProviderClient):
    provider_name = "openai"

    def classify_company(self, company_payload: Dict[str, Any]) -> Dict[str, Any]:
        company_name = company_payload.get("company_display") or company_payload.get("company") or "unknown"

        return {
            "company_name": company_name,
            "classification": "unknown",
            "confidence": 0.0,
            "provider": self.provider_name,
            "mode": "stub",
        }

    def _normalize_text(self, value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()

    def _tokenize(self, value: Any) -> List[str]:
        text = self._normalize_text(value)
        if not text:
            return []
        return [token for token in text.split() if token]

    def _core_tokens(self, company_name: str) -> List[str]:
        stopwords = {
            "the",
            "and",
            "group",
            "holding",
            "holdings",
            "company",
            "companies",
            "global",
            "international",
            "latam",
            "mexico",
            "colombia",
            "ecuador",
            "spain",
            "españa",
            "sa",
            "sas",
            "s a",
            "llc",
            "inc",
            "corp",
            "co",
            "ltd",
            "sl",
            "s l",
            "de",
            "del",
        }
        tokens = self._tokenize(company_name)
        core = [t for t in tokens if t not in stopwords]
        return core or tokens[:1]

    def _is_aggregator_domain(self, domain: str) -> bool:
        normalized = self._normalize_text(domain)
        return any(hint in normalized for hint in AGGREGATOR_HINTS)

    def _candidate_text(self, candidate: Dict[str, Any]) -> str:
        return " ".join(
            [
                str(candidate.get("domain") or ""),
                str(candidate.get("title") or ""),
                str(candidate.get("snippet") or ""),
            ]
        ).lower()

    def _is_suspicious_subdomain(self, domain: str) -> bool:
        normalized = str(domain or "").strip().lower()
        if not normalized:
            return False

        parts = [p for p in normalized.split(".") if p]
        if len(parts) < 3:
            return False

        suspicious_prefixes = {
            "beta",
            "staging",
            "stage",
            "dev",
            "test",
            "qa",
            "sandbox",
            "preview",
            "demo",
            "internal",
        }

        return parts[0] in suspicious_prefixes

    def validate_domain_candidates(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        company_name = str(payload.get("company_name") or "").strip()
        candidates = payload.get("candidates") or []

        if not company_name or not candidates:
            return {
                "selected_domain": None,
                "decision": "rejected",
                "confidence": 0.0,
                "reason": "missing_company_or_candidates",
            }

        core_tokens = self._core_tokens(company_name)
        best_candidate = None
        best_score = -1.0

        for candidate in candidates:
            domain = str(candidate.get("domain") or "").strip().lower()
            title = str(candidate.get("title") or "")
            snippet = str(candidate.get("snippet") or "")
            source = str(candidate.get("source") or "")
            text = self._candidate_text(candidate)

            if not domain:
                continue

            if self._is_aggregator_domain(domain):
                candidate_score = -1.0
            else:
                token_hits = sum(1 for token in core_tokens if token and token in text)
                domain_hits = sum(1 for token in core_tokens if token and token in domain)
                official_bonus = 1 if "official" in text or "sitio oficial" in text else 0
                serp_bonus = 0.25 if source == "serpapi_fallback" else 0.0

                candidate_score = (domain_hits * 2.0) + token_hits + official_bonus + serp_bonus

            if candidate_score > best_score:
                best_score = candidate_score
                best_candidate = candidate

        if not best_candidate:
            return {
                "selected_domain": None,
                "decision": "rejected",
                "confidence": 0.0,
                "reason": "no_viable_candidate",
            }

        domain = str(best_candidate.get("domain") or "").strip().lower()
        text = self._candidate_text(best_candidate)
        domain_hits = sum(1 for token in core_tokens if token and token in domain)
        text_hits = sum(1 for token in core_tokens if token and token in text)
        total_hits = len({token for token in core_tokens if token and token in text})

        if self._is_aggregator_domain(domain):
            return {
                "selected_domain": None,
                "decision": "rejected",
                "confidence": 0.05,
                "reason": "aggregator_domain",
            }

        if self._is_suspicious_subdomain(domain):
            return {
                "selected_domain": domain,
                "decision": "review",
                "confidence": 0.45,
                "reason": "suspicious_subdomain",
            }

        if domain_hits >= 1 and text_hits >= 1:
            return {
                "selected_domain": domain,
                "decision": "accepted",
                "confidence": 0.90,
                "reason": "brand_and_text_match",
            }

        if domain_hits >= 1 and total_hits >= 2:
            return {
                "selected_domain": domain,
                "decision": "accepted",
                "confidence": 0.82,
                "reason": "strong_partial_brand_match",
            }

        if domain_hits >= 1:
            return {
                "selected_domain": domain,
                "decision": "review",
                "confidence": 0.65,
                "reason": "domain_brand_match_only",
            }

        if total_hits >= 2:
            return {
                "selected_domain": domain,
                "decision": "review",
                "confidence": 0.60,
                "reason": "partial_brand_match",
            }

        if text_hits >= 1:
            return {
                "selected_domain": domain,
                "decision": "review",
                "confidence": 0.55,
                "reason": "text_brand_match_only",
            }

        return {
            "selected_domain": None,
            "decision": "rejected",
            "confidence": 0.10,
            "reason": "insufficient_brand_match",
        }
