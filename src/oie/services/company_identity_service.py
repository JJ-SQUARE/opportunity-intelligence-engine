from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.utils.domain_filters import is_job_board_domain
from oie.persistence.repositories import CompanyAliasRepository, CompanyRepository
from oie.persistence.sqlite import initialize_database


LEGAL_SUFFIXES = {
    "inc",
    "inc.",
    "llc",
    "l.l.c.",
    "ltd",
    "ltd.",
    "corp",
    "corp.",
    "corporation",
    "gmbh",
    "s.a.",
    "sa",
    "s.a",
    "plc",
    "limited",
    "co",
    "co.",
}

GENERIC_BUSINESS_TERMS = {
    "technologies",
    "technology",
    "solutions",
    "solution",
    "systems",
    "group",
    "holding",
    "holdings",
    "international",
    "global",
    "labs",
    "lab",
    "digital",
    "services",
    "partners",
    "partner",
}

STOP_ROOT_TOKENS = {
    "and",
}


class CompanyIdentityService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        db_path = self.ctx.config.get("database", {}).get("path", "data/oie.db")
        self.db_path = db_path
        initialize_database(self.db_path)
        self.company_repository = CompanyRepository(db_path)
        self.company_alias_repository = CompanyAliasRepository(db_path)

    def normalize_company_name(self, company_name: str) -> str:
        value = (company_name or "").strip().lower()
        value = value.replace("&", " and ")
        value = re.sub(r"[^\w\s]", " ", value)
        tokens = [
            token
            for token in value.split()
            if token
            and token not in LEGAL_SUFFIXES
        ]
        normalized = " ".join(tokens)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized or "unknown"

    def normalize_company_root(self, company_name: str) -> str:
        normalized = self.normalize_company_name(company_name)
        tokens = [
            token for token in normalized.split()
            if token not in GENERIC_BUSINESS_TERMS
            and token not in STOP_ROOT_TOKENS
        ]
        root = " ".join(tokens).strip()
        return root or normalized

    def build_company_key(self, company_normalized: str, resolved_domain: str | None = None) -> str:
        identity_basis = f"{company_normalized}|{resolved_domain or ''}"
        digest = hashlib.sha1(identity_basis.encode("utf-8")).hexdigest()[:16]
        return f"cmp_{digest}"

    def get_manual_alias_map(self) -> Dict[str, List[str]]:
        return (
            self.ctx.config.get("company_identity", {}).get("manual_aliases", {}) or {}
        )

    def get_merge_rules(self) -> Dict[str, Any]:
        return (
            self.ctx.config.get("company_identity", {}).get("merge_rules", {}) or {}
        )

    def build_aliases(self, company_display: str, company_normalized: str) -> tuple[List[str], Dict[str, str]]:
        aliases = [company_display]
        alias_type_map: Dict[str, str] = {
            company_display: company_normalized,
            f"{company_display}__type": "observed_name",
        }

        manual_aliases = self.get_manual_alias_map()
        for canonical_name, alias_values in manual_aliases.items():
            normalized_canonical = self.normalize_company_name(canonical_name)
            if normalized_canonical == company_normalized:
                for alias in alias_values:
                    if alias not in aliases:
                        aliases.append(alias)
                    alias_type_map[alias] = self.normalize_company_name(alias)
                    alias_type_map[f"{alias}__type"] = "manual_alias"

        return aliases, alias_type_map

    def reconcile_existing_company_key(
        self,
        company_normalized: str,
        resolved_domain: str | None,
        aliases: List[str],
    ) -> str | None:
        existing = self.company_repository.find_by_normalized_and_domain(
            company_normalized=company_normalized,
            resolved_domain=resolved_domain,
        )
        if existing:
            self.ctx.metrics["company_identity_reused_by_normalized_domain"] = (
                int(self.ctx.metrics.get("company_identity_reused_by_normalized_domain", 0)) + 1
            )
            return existing["company_key"]

        if resolved_domain and not is_job_board_domain(resolved_domain):
            existing = self.company_repository.find_by_domain(resolved_domain)
            if existing:
                self.ctx.metrics["company_identity_reused_by_domain"] = (
                    int(self.ctx.metrics.get("company_identity_reused_by_domain", 0)) + 1
                )
                return existing["company_key"]

        for alias in aliases:
            alias_normalized = self.normalize_company_name(alias)
            existing = self.company_alias_repository.find_company_by_alias_normalized(alias_normalized)
            if existing:
                self.ctx.metrics["company_identity_reused_by_alias"] = (
                    int(self.ctx.metrics.get("company_identity_reused_by_alias", 0)) + 1
                )
                return existing["company_key"]

        return None


    def _tokenize_identity_value(self, value: str | None) -> set[str]:
        if not value:
            return set()
        parts = re.split(r"[^a-z0-9]+", value.lower())
        stopwords = {
            "sa", "s", "de", "cv", "llc", "inc", "corp", "co", "company",
            "group", "solutions", "solution", "technology", "technologies",
            "tech", "digital", "systems", "services", "service", "global",
            "latam", "mx", "sas", "ltda"
        }
        return {p for p in parts if p and p not in stopwords and len(p) >= 3}

    def _have_shared_resolved_domain(
        self,
        left: dict,
        right: dict,
    ) -> bool:
        left_domain = (left.get("resolved_domain") or "").strip().lower()
        right_domain = (right.get("resolved_domain") or "").strip().lower()
        return bool(left_domain and right_domain and left_domain == right_domain)

    def _is_safe_same_root_merge(
        self,
        left: dict,
        right: dict,
    ) -> bool:
        left_norm = (left.get("company_normalized") or "").strip().lower()
        right_norm = (right.get("company_normalized") or "").strip().lower()

        if not left_norm or not right_norm:
            return False

        if left_norm == right_norm:
            return True

        if self._have_shared_resolved_domain(left, right):
            return True

        left_tokens = self._tokenize_identity_value(left_norm)
        right_tokens = self._tokenize_identity_value(right_norm)

        if not left_tokens or not right_tokens:
            return False

        shared = left_tokens & right_tokens

        # exigir superposición fuerte; un solo token genérico no basta
        if len(shared) >= 2:
            return True

        # si solo comparten 1 token, solo permitir cuando uno contiene al otro
        # y además el token compartido es claramente la marca principal
        if len(shared) == 1:
            token = next(iter(shared))
            if token in left_norm and token in right_norm:
                if left_norm.startswith(token) or right_norm.startswith(token):
                    if left_norm in right_norm or right_norm in left_norm:
                        return True

        return False


    def detect_merge_candidates(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        merge_rules = self.get_merge_rules()
        allow_same_domain = bool(merge_rules.get("allow_same_domain", True))
        allow_same_root = bool(merge_rules.get("allow_same_root", True))
        allow_same_normalized = bool(merge_rules.get("allow_same_normalized", True))

        for i, left in enumerate(companies):
            for right in companies[i + 1:]:
                if left["company_key"] == right["company_key"]:
                    continue

                left_norm = left.get("company_normalized")
                right_norm = right.get("company_normalized")
                left_root = left.get("company_root")
                right_root = right.get("company_root")
                left_domain = left.get("resolved_domain")
                right_domain = right.get("resolved_domain")
                if is_job_board_domain(left_domain):
                    left_domain = ""
                if is_job_board_domain(right_domain):
                    right_domain = ""

                if allow_same_normalized and left_norm and right_norm and left_norm == right_norm:
                    candidates.append(
                        {
                            "company_key_left": left["company_key"],
                            "company_key_right": right["company_key"],
                            "reason": "same_company_normalized",
                            "confidence": 0.95,
                        }
                    )
                    continue

                if allow_same_root and left_root and right_root and left_root == right_root:
                    confidence = 0.8
                    reason = "same_company_root"

                    if left_domain and right_domain and left_domain == right_domain:
                        confidence = 0.98
                        reason = "same_company_root_and_domain"

                    candidates.append(
                        {
                            "company_key_left": left["company_key"],
                            "company_key_right": right["company_key"],
                            "reason": reason,
                            "confidence": confidence,
                        }
                    )
                    continue

                if allow_same_domain and left_domain and right_domain and left_domain == right_domain:
                    candidates.append(
                        {
                            "company_key_left": left["company_key"],
                            "company_key_right": right["company_key"],
                            "reason": "same_domain",
                            "confidence": 0.9,
                        }
                    )

        return candidates

    def dedupe_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        unique: Dict[tuple[str, str], Dict[str, Any]] = {}

        for company in companies:
            dedupe_key = (
                company.get("company_normalized") or "unknown",
                company.get("resolved_domain") or "",
            )

            if dedupe_key not in unique:
                unique[dedupe_key] = dict(company)
                continue

            current = unique[dedupe_key]
            current["total_openings"] = max(
                int(current.get("total_openings", 0) or 0),
                int(company.get("total_openings", 0) or 0),
            )
            current["remote_jobs"] = max(
                int(current.get("remote_jobs", 0) or 0),
                int(company.get("remote_jobs", 0) or 0),
            )
            current["contractor_jobs"] = max(
                int(current.get("contractor_jobs", 0) or 0),
                int(company.get("contractor_jobs", 0) or 0),
            )

            current_sources = set(current.get("sources", []))
            new_sources = set(company.get("sources", []))
            current["sources"] = sorted(current_sources | new_sources)

            current_aliases = set(current.get("aliases", []))
            new_aliases = set(company.get("aliases", []))
            current["aliases"] = sorted(current_aliases | new_aliases)

            current_alias_type_map = current.get("alias_type_map", {}) or {}
            new_alias_type_map = company.get("alias_type_map", {}) or {}
            current_alias_type_map.update(new_alias_type_map)
            current["alias_type_map"] = current_alias_type_map

            if not current.get("resolved_domain") and company.get("resolved_domain"):
                current["resolved_domain"] = company.get("resolved_domain")
                current["domain_source"] = company.get("domain_source")
                current["domain_confidence"] = company.get("domain_confidence")

        deduped = list(unique.values())
        self.ctx.metrics["companies_after_identity_dedupe"] = len(deduped)
        return deduped

    def enrich_company_identity(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        enriched: List[Dict[str, Any]] = []

        for company in companies:
            display = (company.get("company") or "").strip() or "unknown"
            normalized = self.normalize_company_name(display)
            root = self.normalize_company_root(display)
            resolved_domain = company.get("resolved_domain")
            if is_job_board_domain(resolved_domain):
                resolved_domain = None

            aliases, alias_type_map = self.build_aliases(display, normalized)
            existing_company_key = self.reconcile_existing_company_key(
                company_normalized=normalized,
                resolved_domain=resolved_domain,
                aliases=aliases,
            )

            record = dict(company)
            record["company_display"] = display
            record["company_normalized"] = normalized
            record["company_root"] = root
            record["company_key"] = existing_company_key or self.build_company_key(normalized, resolved_domain)
            record["aliases"] = aliases
            record["alias_type_map"] = alias_type_map

            enriched.append(record)

        deduped = self.dedupe_companies(enriched)
        merge_candidates = self.detect_merge_candidates(deduped)

        self.ctx.metrics["companies_with_identity"] = len(deduped)
        self.ctx.metrics["company_merge_candidates_detected"] = len(merge_candidates)
        self.ctx.metrics["company_identity_completed"] = True
        self.ctx.provider_state["company_merge_candidates"] = merge_candidates

        return deduped
