from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.persistence.sqlite import initialize_database
from oie.services.cached_provider_service import CachedProviderService
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import (
    ProviderExecutionBlockedError,
    ProviderExecutionError,
    ProviderExecutionService,
)
from oie.utils.domain_filters import is_job_board_domain


PLACEHOLDER_COMPANY_VALUES = {
    "",
    "unknown",
    "confidential",
    "stealth",
    "undisclosed",
    "n/a",
    "na",
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

        self.db_path = self.ctx.config.get("database", {}).get("path", "data/oie.db")

        enrichment_cfg = self.ctx.config.get("enrichment", {}) or {}
        self.ttl_days = int(enrichment_cfg.get("apollo_company_ttl_days", 30))
        self.max_companies_per_run = int(enrichment_cfg.get("max_companies_per_run", 5))
        self.min_opportunity_score = float(enrichment_cfg.get("min_opportunity_score", 15))
        self.require_accepted_domain = bool(enrichment_cfg.get("require_accepted_domain", True))
        self.allowed_company_types = {
            str(v).strip().lower()
            for v in enrichment_cfg.get("allowed_company_types", ["end_client", "unknown", ""])
        }

        initialize_database(self.db_path)

    def _is_placeholder_company_name(self, company: Dict[str, Any]) -> bool:
        values = [
            str(company.get("company_display") or "").strip().lower(),
            str(company.get("company") or "").strip().lower(),
            str(company.get("company_normalized") or "").strip().lower(),
        ]
        return any(value in PLACEHOLDER_COMPANY_VALUES for value in values if value)

    def _is_recently_enriched(self, company_key: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            try:
                row = conn.execute(
                    """
                    SELECT enriched_at
                    FROM companies
                    WHERE company_key = ?
                    LIMIT 1
                    """,
                    (company_key,),
                ).fetchone()
            except sqlite3.OperationalError:
                return False
        finally:
            conn.close()

        if not row or not row["enriched_at"]:
            return False

        try:
            enriched_at = datetime.fromisoformat(row["enriched_at"])
        except ValueError:
            return False

        now = datetime.now(UTC)
        if enriched_at.tzinfo is None:
            enriched_at = enriched_at.replace(tzinfo=UTC)

        return (now - enriched_at) <= timedelta(days=self.ttl_days)

    def _should_attempt_enrichment(self, company: Dict[str, Any]) -> bool:
        company_key = company.get("company_key")
        domain = (company.get("resolved_domain") or "").strip().lower()
        validation_status = (company.get("domain_validation_status") or "").strip().lower()
        company_type = (company.get("company_type_ai") or "").strip().lower()
        classification_confidence = float(company.get("classification_confidence_ai") or 0.0)
        opportunity_score = float(company.get("opportunity_score") or 0.0)

        if not company_key or not domain:
            return False

        if self._is_placeholder_company_name(company):
            return False

        if is_job_board_domain(domain):
            return False

        if self.require_accepted_domain and validation_status and validation_status != "accepted":
            return False

        if validation_status == "review":
            return False

        if domain in self._failed_enrichment_domains:
            return False

        if company_type and company_type not in self.allowed_company_types and classification_confidence >= 0.75:
            return False

        if opportunity_score > 0 and opportunity_score < self.min_opportunity_score:
            return False

        return True

    def _priority(self, company: Dict[str, Any]) -> tuple:
        opportunity_score = float(company.get("opportunity_score") or 0.0)
        company_type = (company.get("company_type_ai") or "").strip().lower()
        validation_status = (company.get("domain_validation_status") or "").strip().lower()
        recently_enriched = self._is_recently_enriched(company.get("company_key") or "")

        return (
            1 if validation_status == "accepted" else 0,
            1 if company_type == "end_client" else 0,
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
                    mapped = self._map_apollo_payload(payload)
                    record.update(mapped)
                    enriched_count += 1
            except (ProviderExecutionBlockedError, ProviderExecutionError, ValueError):
                if domain:
                    self._failed_enrichment_domains.add(domain)

            enriched_companies.append(record)

        self.ctx.metrics["companies_enriched"] = enriched_count
        self.ctx.metrics["companies_enrichment_skipped_ttl"] = skipped_ttl_count
        return enriched_companies
