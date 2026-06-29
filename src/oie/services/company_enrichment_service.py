from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.persistence.context import PersistenceContext
from oie.persistence.repositories import CompanyRepository
from oie.persistence.sqlite import initialize_database
from oie.services.cached_provider_service import CachedProviderService
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import (
    ProviderExecutionBlockedError,
    ProviderExecutionError,
    ProviderExecutionService,
)
from oie.utils.domain_filters import is_job_board_domain
from oie.utils.company_identity_utils import is_actionable_company_name
from oie.utils.company_name_extraction import extract_actionable_company_name
from oie.services.domain_confidence_service import DomainConfidenceService


PLACEHOLDER_COMPANY_VALUES = {
    "",
    "unknown",
    "confidential",
    "stealth",
    "undisclosed",
    "n/a",
    "na",
}


COMPANY_TYPE_ALIASES = {
    "staffing_agency": "staffing",
    "outsourcing": "consulting",
    "product_company": "end_client",
}


class CompanyEnrichmentService:
    def __init__(
        self,
        ctx: RunContext,
        provider_control_service: ProviderControlService,
    ) -> None:
        self.ctx = ctx
        self.provider_control_service = provider_control_service
        self.provider_execution_service = ProviderExecutionService(ctx, provider_control_service)
        self.cached_provider_service = CachedProviderService(ctx)

        failed_enrichment_domains = self.ctx.provider_state.get("failed_enrichment_domains")
        if not isinstance(failed_enrichment_domains, set):
            failed_enrichment_domains = set()
            self.ctx.provider_state["failed_enrichment_domains"] = failed_enrichment_domains
        self._failed_enrichment_domains = failed_enrichment_domains

        self.persistence = PersistenceContext.from_run_context(ctx)
        self.db_path = self.persistence.path or self.ctx.paths.get("db_path") or self.ctx.config.get("database", {}).get("path", "data/oie.db")
        self.company_repository = CompanyRepository(persistence=self.persistence)

        enrichment_cfg = self.ctx.config.get("enrichment", {}) or {}
        self.ttl_days = int(enrichment_cfg.get("apollo_company_ttl_days", 30))
        self.max_companies_per_run = int(enrichment_cfg.get("max_companies_per_run", 5))
        self.min_opportunity_score = float(enrichment_cfg.get("min_opportunity_score", 15))
        self.require_accepted_domain = bool(enrichment_cfg.get("require_accepted_domain", True))
        self.allowed_company_types = {
            str(v).strip().lower()
            for v in enrichment_cfg.get("allowed_company_types", ["end_client", "unknown", ""])
        }
        self.min_domain_match_confidence = float(enrichment_cfg.get("min_domain_match_confidence", 0.80))
        self.domain_confidence_service = DomainConfidenceService()

        if self.persistence.backend == "sqlite":
            initialize_database(self.db_path)

    def _is_placeholder_company_name(self, company: Dict[str, Any]) -> bool:
        values = [
            str(company.get("company_display") or "").strip().lower(),
            str(company.get("company") or "").strip().lower(),
            str(company.get("company_normalized") or "").strip().lower(),
        ]
        return any(value in PLACEHOLDER_COMPANY_VALUES for value in values if value)

    def _is_recently_enriched(self, company_key: str) -> bool:
        if not company_key:
            return False

        try:
            row = self.company_repository.get_company_by_key(company_key)
        except Exception:
            return False

        if not row or not row.get("enriched_at"):
            return False

        try:
            enriched_at = datetime.fromisoformat(row["enriched_at"])
        except ValueError:
            return False

        now = datetime.now(UTC)
        if enriched_at.tzinfo is None:
            enriched_at = enriched_at.replace(tzinfo=UTC)

        return (now - enriched_at) <= timedelta(days=self.ttl_days)

    def _best_company_name_for_validation(self, company: Dict[str, Any]) -> str:
        extracted = extract_actionable_company_name(
            company_display=company.get("company_display") or company.get("company"),
            title=company.get("title"),
            snippet=company.get("snippet") or company.get("company_description") or company.get("description"),
            apply_url=company.get("apply_url"),
        )
        if extracted:
            return extracted

        for value in (
            company.get("company_display"),
            company.get("company"),
            company.get("company_normalized"),
        ):
            cleaned = str(value or "").strip()
            if cleaned and is_actionable_company_name(cleaned):
                return cleaned
        return ""

    def _is_suspicious_domain_for_enrichment(self, domain: str) -> bool:
        lowered = str(domain or "").strip().lower()
        if not lowered:
            return True

        suspicious_subdomain_markers = (
            "beta.",
            "staging.",
            "stage.",
            "dev.",
            "test.",
            "qa.",
            "uat.",
            "sandbox.",
            "preview.",
            "demo.",
            "internal.",
        )
        if any(lowered.startswith(marker) for marker in suspicious_subdomain_markers):
            return True

        return False

    def _has_strong_company_domain_match(self, company: Dict[str, Any]) -> bool:
        domain = (company.get("resolved_domain") or "").strip().lower()
        if not domain:
            return False

        company_name = self._best_company_name_for_validation(company)
        if not company_name:
            return False

        scored = self.domain_confidence_service.score_candidate(
            company_name=company_name,
            domain=domain,
            source="apply_url",
            serp_rank=None,
            title="",
            snippet="",
        )
        return (
            not bool(scored.get("confidence_blocked"))
            and float(scored.get("score") or 0.0) >= self.min_domain_match_confidence
        )

    def _normalized_company_type(self, value: Any) -> str:
        normalized = str(value or "").strip().lower()
        return COMPANY_TYPE_ALIASES.get(normalized, normalized)


    def _has_end_client_enrichment_fallback(self, company: Dict[str, Any]) -> bool:
        validation_status = (company.get("domain_validation_status") or "").strip().lower()
        company_type = self._normalized_company_type(company.get("company_type_ai") or "")
        classification_confidence = float(company.get("classification_confidence_ai") or 0.0)
        opportunity_score = float(company.get("opportunity_score") or 0.0)

        if validation_status not in {"accepted", "accepted_ai_validated"}:
            return False

        if company_type not in {"end_client", "product_company"}:
            return False

        if classification_confidence < 0.90:
            return False

        if opportunity_score > 0 and opportunity_score < self.min_opportunity_score:
            return False

        domain = (company.get("resolved_domain") or "").strip().lower()
        if not domain:
            return False

        if is_job_board_domain(domain):
            return False

        if self._is_suspicious_domain_for_enrichment(domain):
            return False

        company_name = self._best_company_name_for_validation(company)
        if not company_name:
            return False

        scored = self.domain_confidence_service.score_candidate(
            company_name=company_name,
            domain=domain,
            source="serpapi_fallback",
            serp_rank=1,
            title=str(company.get("title") or company.get("company_display") or ""),
            snippet=str(company.get("snippet") or company.get("company_description") or company.get("description") or ""),
        )

        if bool(scored.get("confidence_blocked")):
            return False

        if not bool(scored.get("confidence_brand_match")):
            return False

        if str(scored.get("validation_status") or "").strip().lower() == "rejected":
            return False

        return float(scored.get("score") or 0.0) >= self.domain_confidence_service.review_threshold

    def _should_attempt_enrichment(self, company: Dict[str, Any]) -> bool:
        company_key = company.get("company_key")
        domain = (company.get("resolved_domain") or "").strip().lower()
        validation_status = (company.get("domain_validation_status") or "").strip().lower()
        company_type = self._normalized_company_type(company.get("company_type_ai") or "")
        classification_confidence = float(company.get("classification_confidence_ai") or 0.0)
        opportunity_score = float(company.get("opportunity_score") or 0.0)

        if company.get("benchmark_only") or company_type == "competitor":
            return False

        if not company_key or not domain:
            return False

        if self._is_placeholder_company_name(company):
            return False

        if not self._best_company_name_for_validation(company):
            return False

        if is_job_board_domain(domain):
            return False

        if self._is_suspicious_domain_for_enrichment(domain):
            return False

        if self.require_accepted_domain and validation_status and validation_status not in {"accepted", "accepted_ai_validated"}:
            return False

        if validation_status == "review":
            return False

        if domain in self._failed_enrichment_domains:
            return False

        if company_type and company_type not in self.allowed_company_types and classification_confidence >= 0.75:
            return False

        if opportunity_score > 0 and opportunity_score < self.min_opportunity_score:
            return False

        if not self._has_strong_company_domain_match(company):
            if not self._has_end_client_enrichment_fallback(company):
                return False

        return True

    def _priority(self, company: Dict[str, Any]) -> tuple:
        opportunity_score = float(company.get("opportunity_score") or 0.0)
        company_type = self._normalized_company_type(company.get("company_type_ai") or "")
        validation_status = (company.get("domain_validation_status") or "").strip().lower()
        recently_enriched = self._is_recently_enriched(company.get("company_key") or "")

        return (
            1 if validation_status in {"accepted", "accepted_ai_validated"} else 0,
            1 if company_type in {"end_client", "product_company"} else 0,
            0 if recently_enriched else 1,
            opportunity_score,
        )

    def _map_apollo_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        organization = payload.get("organization") or payload

        return {
            "industry": organization.get("industry") or "",
            "employee_range": organization.get("estimated_num_employees") or "",
            "linkedin_company_url": organization.get("linkedin_url") or "",
            "company_description": organization.get("short_description") or organization.get("description") or "",
            "company_size": organization.get("estimated_num_employees") or "",
            "enriched_at": datetime.now(UTC).isoformat(),
            "enrichment_source": "apollo",
        }

    def enrich_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self.ctx.flags.get("no_enrichment"):
            self.ctx.metrics["company_enrichment_skipped_no_enrichment"] = True
            return companies

        client = self.provider_control_service.registry.get_client("apollo")
        if client is None:
            self.ctx.metrics["company_enrichment_skipped_no_client"] = True
            return companies

        enriched_companies: List[Dict[str, Any]] = []
        enriched_count = 0
        skipped_ttl_count = 0
        rejected_by_ai_count = 0
        buyer_personas_generated_count = 0

        eligible_indexes = [
            idx for idx, company in enumerate(companies)
            if self._should_attempt_enrichment(company)
        ]
        eligible_indexes.sort(key=lambda idx: self._priority(companies[idx]), reverse=True)
        selected_indexes = set(eligible_indexes[: self.max_companies_per_run])

        self.ctx.metrics["company_enrichment_candidates_total"] = len(eligible_indexes)
        self.ctx.metrics["company_enrichment_selected_total"] = len(selected_indexes)
        self.ctx.metrics["company_enrichment_skipped_limit"] = max(len(eligible_indexes) - len(selected_indexes), 0)

        for idx, company in enumerate(companies):
            record = dict(company)
            company_key = record.get("company_key")
            domain = (record.get("resolved_domain") or "").strip().lower()

            if idx not in selected_indexes:
                enriched_companies.append(record)
                continue

            if self._is_recently_enriched(company_key):
                skipped_ttl_count += 1
                enriched_companies.append(record)
                continue

            if domain in self._failed_enrichment_domains:
                enriched_companies.append(record)
                continue

            try:
                if self.db_path == ":memory:":
                    payload = self.provider_execution_service.execute(
                        "apollo",
                        "enrich_company_by_domain",
                        client.enrich_company_by_domain,
                        domain,
                        cost=1,
                    )
                else:
                    payload = self.cached_provider_service.execute_cached(
                        namespace="apollo_company_enrichment",
                        cache_payload={"domain": domain},
                        fn=lambda: self.provider_execution_service.execute(
                            "apollo",
                            "enrich_company_by_domain",
                            client.enrich_company_by_domain,
                            domain,
                            cost=1,
                        ),
                    )
                if payload:
                    openai_client = self.provider_control_service.registry.get_client("openai")
                    if openai_client is not None and hasattr(openai_client, "validate_company_enrichment"):
                        try:
                            validation = self.provider_execution_service.execute(
                                "openai",
                                "validate_company_enrichment",
                                openai_client.validate_company_enrichment,
                                {**record, "apollo_enrichment": payload},
                            )
                        except (ProviderExecutionBlockedError, ProviderExecutionError, ValueError, RuntimeError):
                            validation = {}
                        record.update(validation)
                        if validation.get("enrichment_ai_decision") == "rejected":
                            rejected_by_ai_count += 1
                            enriched_companies.append(record)
                            continue

                    mapped = self._map_apollo_payload(payload)
                    record.update(mapped)

                    if openai_client is not None and hasattr(openai_client, "generate_buyer_personas"):
                        try:
                            personas = self.provider_execution_service.execute(
                                "openai",
                                "generate_buyer_personas",
                                openai_client.generate_buyer_personas,
                                record,
                            )
                        except (ProviderExecutionBlockedError, ProviderExecutionError, ValueError, RuntimeError):
                            personas = {}
                        if personas:
                            record.update(personas)
                            buyer_personas_generated_count += 1

                    enriched_count += 1
            except (ProviderExecutionBlockedError, ProviderExecutionError, ValueError):
                if domain:
                    self._failed_enrichment_domains.add(domain)

            enriched_companies.append(record)

        self.ctx.metrics["companies_enriched"] = enriched_count
        self.ctx.metrics["companies_enrichment_skipped_ttl"] = skipped_ttl_count
        self.ctx.metrics["companies_enrichment_rejected_by_ai"] = rejected_by_ai_count
        self.ctx.metrics["companies_buyer_personas_generated"] = buyer_personas_generated_count
        return enriched_companies
