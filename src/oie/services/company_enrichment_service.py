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
        self.ttl_days = int(
            self.ctx.config.get("enrichment", {}).get("apollo_company_ttl_days", 30)
        )
        initialize_database(self.db_path)

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

        if not company_key or not domain:
            return False

        if validation_status == "review":
            return False

        if is_job_board_domain(domain):
            return False

        if domain in self._failed_enrichment_domains:
            return False

        return True

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

        for company in companies:
            record = dict(company)
            company_key = record.get("company_key")
            domain = (record.get("resolved_domain") or "").strip().lower()

            if not self._should_attempt_enrichment(record):
                enriched_companies.append(record)
                continue

            if self._is_recently_enriched(company_key):
                skipped_ttl_count += 1
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
