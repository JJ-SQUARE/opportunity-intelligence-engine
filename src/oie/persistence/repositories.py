from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any, Dict, List, Optional

from oie.persistence.context import PersistenceContext
from oie.persistence.models import Run, RunMetric, ProviderEvent, ProviderOperationMetric, Company, CompanyAlias, Domain, CompanyMergeCandidate, Job, Lead, CompanyScore
from oie.persistence.session import create_session_factory


class RepositoryBase:
    def __init__(
        self,
        db_path: str = "data/oie.db",
        persistence: PersistenceContext | None = None,
    ) -> None:
        self.db_path = db_path
        self.persistence = persistence or PersistenceContext.from_sqlite_path(db_path)

    def connection(self) -> sqlite3.Connection:
        return self.persistence.connection()

class RunRepository(RepositoryBase):
    def upsert_run(self, run_id: str, run_date: str, status: str, mode: str) -> None:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                conn.execute(
                    """
                    INSERT INTO runs (run_id, run_date, status, mode)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(run_id) DO UPDATE SET
                        run_date = excluded.run_date,
                        status = excluded.status,
                        mode = excluded.mode
                    """,
                    (run_id, run_date, status, mode),
                )
                conn.commit()
            finally:
                conn.close()
            return

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            existing = session.get(Run, run_id)
            if existing is None:
                session.add(
                    Run(
                        run_id=run_id,
                        run_date=run_date,
                        status=status,
                        mode=mode,
                    )
                )
            else:
                existing.run_date = run_date
                existing.status = status
                existing.mode = mode
            session.commit()

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                row = conn.execute(
                    """
                    SELECT run_id, run_date, status, mode, created_at
                    FROM runs
                    WHERE run_id = ?
                    LIMIT 1
                    """,
                    (run_id,),
                ).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            run = session.get(Run, run_id)
            if run is None:
                return None
            return {
                "run_id": run.run_id,
                "run_date": run.run_date,
                "status": run.status,
                "mode": run.mode,
                "created_at": run.created_at,
            }


class RunMetricsRepository(RepositoryBase):
    def replace_metrics(self, run_id: str, metrics: Dict[str, Any]) -> None:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                conn.execute("DELETE FROM run_metrics WHERE run_id = ?", (run_id,))
                conn.executemany(
                    """
                    INSERT INTO run_metrics (run_id, metric_key, metric_value)
                    VALUES (?, ?, ?)
                    """,
                    [(run_id, key, str(value)) for key, value in metrics.items()],
                )
                conn.commit()
            finally:
                conn.close()
            return

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            session.query(RunMetric).filter(RunMetric.run_id == run_id).delete()
            session.add_all(
                [
                    RunMetric(
                        run_id=run_id,
                        metric_key=str(key),
                        metric_value=str(value),
                    )
                    for key, value in metrics.items()
                ]
            )
            session.commit()

    def get_metrics(self, run_id: str) -> Dict[str, Any]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                rows = conn.execute(
                    """
                    SELECT metric_key, metric_value
                    FROM run_metrics
                    WHERE run_id = ?
                    ORDER BY metric_key ASC
                    """,
                    (run_id,),
                ).fetchall()
                return {row["metric_key"]: row["metric_value"] for row in rows}
            finally:
                conn.close()

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            rows = (
                session.query(RunMetric)
                .filter(RunMetric.run_id == run_id)
                .order_by(RunMetric.metric_key.asc())
                .all()
            )
            return {row.metric_key: row.metric_value for row in rows}


class ProviderEventRepository(RepositoryBase):
    def replace_events(self, run_id: str, provider_events: List[Dict[str, Any]]) -> None:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                conn.execute("DELETE FROM provider_events WHERE run_id = ?", (run_id,))
                conn.executemany(
                    """
                    INSERT INTO provider_events (run_id, provider, event_type, status_code, message, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            run_id,
                            event.get("provider"),
                            event.get("event_type"),
                            event.get("status_code"),
                            event.get("message"),
                            json.dumps(event.get("metadata", {}), ensure_ascii=False),
                        )
                        for event in provider_events
                    ],
                )
                conn.commit()
            finally:
                conn.close()
            return

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            session.query(ProviderEvent).filter(ProviderEvent.run_id == run_id).delete()
            session.add_all(
                [
                    ProviderEvent(
                        run_id=run_id,
                        provider=str(event.get("provider") or ""),
                        event_type=str(event.get("event_type") or ""),
                        status_code=event.get("status_code"),
                        message=event.get("message"),
                        metadata_json=json.dumps(event.get("metadata", {}), ensure_ascii=False),
                    )
                    for event in provider_events
                ]
            )
            session.commit()

    def list_by_run(self, run_id: str) -> List[Dict[str, Any]]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                rows = conn.execute(
                    """
                    SELECT run_id, provider, event_type, status_code, message, metadata_json, created_at
                    FROM provider_events
                    WHERE run_id = ?
                    ORDER BY id ASC
                    """,
                    (run_id,),
                ).fetchall()

                out: List[Dict[str, Any]] = []
                for row in rows:
                    record = dict(row)
                    metadata_json = record.get("metadata_json")
                    try:
                        record["metadata"] = json.loads(metadata_json) if metadata_json else {}
                    except Exception:
                        record["metadata"] = {}
                    out.append(record)
                return out
            finally:
                conn.close()

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            rows = (
                session.query(ProviderEvent)
                .filter(ProviderEvent.run_id == run_id)
                .order_by(ProviderEvent.id.asc())
                .all()
            )

            out: List[Dict[str, Any]] = []
            for row in rows:
                try:
                    metadata = json.loads(row.metadata_json) if row.metadata_json else {}
                except Exception:
                    metadata = {}
                out.append(
                    {
                        "run_id": row.run_id,
                        "provider": row.provider,
                        "event_type": row.event_type,
                        "status_code": row.status_code,
                        "message": row.message,
                        "metadata_json": row.metadata_json,
                        "created_at": row.created_at,
                        "metadata": metadata,
                    }
                )
            return out



class ProviderOperationMetricsRepository(RepositoryBase):
    def replace_rows(self, run_id: str, rows: List[Dict[str, Any]]) -> None:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                conn.execute("DELETE FROM provider_operation_metrics WHERE run_id = ?", (run_id,))
                if rows:
                    conn.executemany(
                        """
                        INSERT INTO provider_operation_metrics (
                            run_id,
                            provider,
                            operation,
                            max_calls,
                            used_calls,
                            remaining_calls,
                            started,
                            success,
                            retry_count,
                            blocked_budget,
                            blocked_provider,
                            errors_timeout,
                            errors_rate_limit,
                            errors_http_5xx,
                            errors_execution_error,
                            errors_auth,
                            errors_permission
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            (
                                run_id,
                                row.get("provider"),
                                row.get("operation"),
                                row.get("max_calls"),
                                row.get("used_calls", 0),
                                row.get("remaining_calls"),
                                row.get("started", 0),
                                row.get("success", 0),
                                row.get("retry_count", 0),
                                row.get("blocked_budget", 0),
                                row.get("blocked_provider", 0),
                                row.get("errors_timeout", 0),
                                row.get("errors_rate_limit", 0),
                                row.get("errors_http_5xx", 0),
                                row.get("errors_execution_error", 0),
                                row.get("errors_auth", 0),
                                row.get("errors_permission", 0),
                            )
                            for row in rows
                        ],
                    )
                conn.commit()
            finally:
                conn.close()
            return

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            session.query(ProviderOperationMetric).filter(
                ProviderOperationMetric.run_id == run_id
            ).delete()
            session.add_all(
                [
                    ProviderOperationMetric(
                        run_id=run_id,
                        provider=str(row.get("provider") or ""),
                        operation=str(row.get("operation") or ""),
                        max_calls=row.get("max_calls"),
                        used_calls=int(row.get("used_calls", 0) or 0),
                        remaining_calls=row.get("remaining_calls"),
                        started=int(row.get("started", 0) or 0),
                        success=int(row.get("success", 0) or 0),
                        retry_count=int(row.get("retry_count", 0) or 0),
                        blocked_budget=int(row.get("blocked_budget", 0) or 0),
                        blocked_provider=int(row.get("blocked_provider", 0) or 0),
                        errors_timeout=int(row.get("errors_timeout", 0) or 0),
                        errors_rate_limit=int(row.get("errors_rate_limit", 0) or 0),
                        errors_http_5xx=int(row.get("errors_http_5xx", 0) or 0),
                        errors_execution_error=int(row.get("errors_execution_error", 0) or 0),
                        errors_auth=int(row.get("errors_auth", 0) or 0),
                        errors_permission=int(row.get("errors_permission", 0) or 0),
                    )
                    for row in rows
                ]
            )
            session.commit()


class CompanyRepository(RepositoryBase):
    def upsert_companies(self, companies: List[Dict[str, Any]]) -> None:
        if self.persistence.backend != "sqlite":
            self._upsert_companies_orm(companies)
            return

        conn = self.connection()
        try:
            conn.executemany(
                """
                INSERT INTO companies (
                    company_key,
                    company_display,
                    company_normalized,
                    company_root,
                    resolved_domain,
                    domain_source,
                    domain_confidence,
                    domain_candidate,
                    domain_validation_status,
                    domain_review_required,
                    domain_ai_validated,
                    domain_ai_decision,
                    domain_ai_confidence,
                    domain_ai_reason,
                    ai_company_identity_confidence,
                    ai_company_identity_source,
                    ai_company_identity_reason,
                    company_identity_ai_valid,
                    company_identity_ai_contaminated,
                    company_identity_ai_ambiguous,
                    industry,
                    employee_range,
                    linkedin_company_url,
                    company_description,
                    company_size,
                    enriched_at,
                    enrichment_source,
                    enrichment_ai_match,
                    enrichment_ai_confidence,
                    enrichment_ai_decision,
                    enrichment_ai_reason,
                    enrichment_ai_provider,
                    enrichment_ai_model,
                    enrichment_ai_mode,
                    company_type_ai,
                    classification_confidence_ai,
                    classification_provider,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(company_key) DO UPDATE SET
                    company_display = excluded.company_display,
                    company_normalized = excluded.company_normalized,
                    company_root = COALESCE(excluded.company_root, companies.company_root),
                    resolved_domain = excluded.resolved_domain,
                    domain_source = excluded.domain_source,
                    domain_confidence = excluded.domain_confidence,
                    domain_candidate = excluded.domain_candidate,
                    domain_validation_status = excluded.domain_validation_status,
                    domain_review_required = excluded.domain_review_required,
                    domain_ai_validated = excluded.domain_ai_validated,
                    domain_ai_decision = excluded.domain_ai_decision,
                    domain_ai_confidence = excluded.domain_ai_confidence,
                    domain_ai_reason = excluded.domain_ai_reason,
                    ai_company_identity_confidence = excluded.ai_company_identity_confidence,
                    ai_company_identity_source = excluded.ai_company_identity_source,
                    ai_company_identity_reason = excluded.ai_company_identity_reason,
                    company_identity_ai_valid = excluded.company_identity_ai_valid,
                    company_identity_ai_contaminated = excluded.company_identity_ai_contaminated,
                    company_identity_ai_ambiguous = excluded.company_identity_ai_ambiguous,
                    industry = COALESCE(excluded.industry, companies.industry),
                    employee_range = COALESCE(excluded.employee_range, companies.employee_range),
                    linkedin_company_url = COALESCE(excluded.linkedin_company_url, companies.linkedin_company_url),
                    company_description = COALESCE(excluded.company_description, companies.company_description),
                    company_size = COALESCE(excluded.company_size, companies.company_size),
                    enriched_at = COALESCE(excluded.enriched_at, companies.enriched_at),
                    enrichment_source = COALESCE(excluded.enrichment_source, companies.enrichment_source),
                    enrichment_ai_match = excluded.enrichment_ai_match,
                    enrichment_ai_confidence = COALESCE(excluded.enrichment_ai_confidence, companies.enrichment_ai_confidence),
                    enrichment_ai_decision = COALESCE(excluded.enrichment_ai_decision, companies.enrichment_ai_decision),
                    enrichment_ai_reason = COALESCE(excluded.enrichment_ai_reason, companies.enrichment_ai_reason),
                    enrichment_ai_provider = COALESCE(excluded.enrichment_ai_provider, companies.enrichment_ai_provider),
                    enrichment_ai_model = COALESCE(excluded.enrichment_ai_model, companies.enrichment_ai_model),
                    enrichment_ai_mode = COALESCE(excluded.enrichment_ai_mode, companies.enrichment_ai_mode),
                    company_type_ai = COALESCE(excluded.company_type_ai, companies.company_type_ai),
                    classification_confidence_ai = COALESCE(excluded.classification_confidence_ai, companies.classification_confidence_ai),
                    classification_provider = COALESCE(excluded.classification_provider, companies.classification_provider),
                    updated_at = CURRENT_TIMESTAMP
                """,
                [
                    (
                        company.get("company_key"),
                        company.get("company_display"),
                        company.get("company_normalized"),
                        company.get("company_root"),
                        company.get("resolved_domain"),
                        company.get("domain_source"),
                        company.get("domain_confidence"),
                        company.get("domain_candidate"),
                        company.get("domain_validation_status"),
                        1 if company.get("domain_review_required") else 0,
                        1 if company.get("domain_ai_validated") else 0,
                        company.get("domain_ai_decision"),
                        company.get("domain_ai_confidence"),
                        company.get("domain_ai_reason"),
                        company.get("ai_company_identity_confidence"),
                        company.get("ai_company_identity_source"),
                        company.get("ai_company_identity_reason"),
                        1 if company.get("company_identity_ai_valid", True) else 0,
                        1 if company.get("company_identity_ai_contaminated") else 0,
                        1 if company.get("company_identity_ai_ambiguous") else 0,
                        company.get("industry"),
                        company.get("employee_range"),
                        company.get("linkedin_company_url"),
                        company.get("company_description"),
                        company.get("company_size"),
                        company.get("enriched_at"),
                        company.get("enrichment_source"),
                        1 if company.get("enrichment_ai_match") else 0,
                        company.get("enrichment_ai_confidence"),
                        company.get("enrichment_ai_decision"),
                        company.get("enrichment_ai_reason"),
                        company.get("enrichment_ai_provider"),
                        company.get("enrichment_ai_model"),
                        company.get("enrichment_ai_mode"),
                        company.get("company_type_ai"),
                        company.get("classification_confidence_ai"),
                        company.get("classification_provider"),
                    )
                    for company in companies
                ],
            )
            conn.commit()
        finally:
            conn.close()
            return

        self._upsert_companies_orm(companies)

    def _coalesce_company_value(self, new_value: Any, existing_value: Any) -> Any:
        return existing_value if new_value is None else new_value

    def _bool_int(self, value: Any, default: bool = False) -> int:
        if value is None:
            return 1 if default else 0
        return 1 if value else 0

    def _company_orm_values(self, company: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "company_key": company.get("company_key"),
            "company_display": company.get("company_display"),
            "company_normalized": company.get("company_normalized"),
            "company_root": company.get("company_root"),
            "resolved_domain": company.get("resolved_domain"),
            "domain_source": company.get("domain_source"),
            "domain_confidence": company.get("domain_confidence"),
            "domain_candidate": company.get("domain_candidate"),
            "domain_validation_status": company.get("domain_validation_status"),
            "domain_review_required": self._bool_int(company.get("domain_review_required")),
            "domain_ai_validated": self._bool_int(company.get("domain_ai_validated")),
            "domain_ai_decision": company.get("domain_ai_decision"),
            "domain_ai_confidence": company.get("domain_ai_confidence"),
            "domain_ai_reason": company.get("domain_ai_reason"),
            "ai_company_identity_confidence": company.get("ai_company_identity_confidence"),
            "ai_company_identity_source": company.get("ai_company_identity_source"),
            "ai_company_identity_reason": company.get("ai_company_identity_reason"),
            "company_identity_ai_valid": self._bool_int(
                company.get("company_identity_ai_valid"),
                default=True,
            ),
            "company_identity_ai_contaminated": self._bool_int(company.get("company_identity_ai_contaminated")),
            "company_identity_ai_ambiguous": self._bool_int(company.get("company_identity_ai_ambiguous")),
            "industry": company.get("industry"),
            "employee_range": company.get("employee_range"),
            "linkedin_company_url": company.get("linkedin_company_url"),
            "company_description": company.get("company_description"),
            "company_size": company.get("company_size"),
            "enriched_at": company.get("enriched_at"),
            "enrichment_source": company.get("enrichment_source"),
            "enrichment_ai_match": self._bool_int(company.get("enrichment_ai_match")),
            "enrichment_ai_confidence": company.get("enrichment_ai_confidence"),
            "enrichment_ai_decision": company.get("enrichment_ai_decision"),
            "enrichment_ai_reason": company.get("enrichment_ai_reason"),
            "enrichment_ai_provider": company.get("enrichment_ai_provider"),
            "enrichment_ai_model": company.get("enrichment_ai_model"),
            "enrichment_ai_mode": company.get("enrichment_ai_mode"),
            "company_type_ai": company.get("company_type_ai"),
            "classification_confidence_ai": company.get("classification_confidence_ai"),
            "classification_provider": company.get("classification_provider"),
        }

    def _upsert_companies_orm(self, companies: List[Dict[str, Any]]) -> None:
        if not companies:
            return

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            for company in companies:
                values = self._company_orm_values(company)
                company_key = values.get("company_key")
                if not company_key:
                    continue

                existing = session.get(Company, company_key)
                if existing is None:
                    session.add(Company(**values))
                    continue

                existing.company_display = values["company_display"]
                existing.company_normalized = values["company_normalized"]
                existing.company_root = self._coalesce_company_value(values["company_root"], existing.company_root)
                existing.resolved_domain = values["resolved_domain"]
                existing.domain_source = values["domain_source"]
                existing.domain_confidence = values["domain_confidence"]
                existing.domain_candidate = values["domain_candidate"]
                existing.domain_validation_status = values["domain_validation_status"]
                existing.domain_review_required = values["domain_review_required"]
                existing.domain_ai_validated = values["domain_ai_validated"]
                existing.domain_ai_decision = values["domain_ai_decision"]
                existing.domain_ai_confidence = values["domain_ai_confidence"]
                existing.domain_ai_reason = values["domain_ai_reason"]
                existing.ai_company_identity_confidence = values["ai_company_identity_confidence"]
                existing.ai_company_identity_source = values["ai_company_identity_source"]
                existing.ai_company_identity_reason = values["ai_company_identity_reason"]
                existing.company_identity_ai_valid = values["company_identity_ai_valid"]
                existing.company_identity_ai_contaminated = values["company_identity_ai_contaminated"]
                existing.company_identity_ai_ambiguous = values["company_identity_ai_ambiguous"]
                existing.industry = self._coalesce_company_value(values["industry"], existing.industry)
                existing.employee_range = self._coalesce_company_value(values["employee_range"], existing.employee_range)
                existing.linkedin_company_url = self._coalesce_company_value(values["linkedin_company_url"], existing.linkedin_company_url)
                existing.company_description = self._coalesce_company_value(values["company_description"], existing.company_description)
                existing.company_size = self._coalesce_company_value(values["company_size"], existing.company_size)
                existing.enriched_at = self._coalesce_company_value(values["enriched_at"], existing.enriched_at)
                existing.enrichment_source = self._coalesce_company_value(values["enrichment_source"], existing.enrichment_source)
                existing.enrichment_ai_match = values["enrichment_ai_match"]
                existing.enrichment_ai_confidence = self._coalesce_company_value(values["enrichment_ai_confidence"], existing.enrichment_ai_confidence)
                existing.enrichment_ai_decision = self._coalesce_company_value(values["enrichment_ai_decision"], existing.enrichment_ai_decision)
                existing.enrichment_ai_reason = self._coalesce_company_value(values["enrichment_ai_reason"], existing.enrichment_ai_reason)
                existing.enrichment_ai_provider = self._coalesce_company_value(values["enrichment_ai_provider"], existing.enrichment_ai_provider)
                existing.enrichment_ai_model = self._coalesce_company_value(values["enrichment_ai_model"], existing.enrichment_ai_model)
                existing.enrichment_ai_mode = self._coalesce_company_value(values["enrichment_ai_mode"], existing.enrichment_ai_mode)
                existing.company_type_ai = self._coalesce_company_value(values["company_type_ai"], existing.company_type_ai)
                existing.classification_confidence_ai = self._coalesce_company_value(values["classification_confidence_ai"], existing.classification_confidence_ai)
                existing.classification_provider = self._coalesce_company_value(values["classification_provider"], existing.classification_provider)

            session.commit()

    def find_by_normalized_and_domain(self, company_normalized: str, resolved_domain: str | None) -> Optional[Dict[str, Any]]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                row = conn.execute(
                    """
                    SELECT company_key, company_display, company_normalized, company_root, resolved_domain
                    FROM companies
                    WHERE company_normalized = ?
                      AND COALESCE(resolved_domain, '') = COALESCE(?, '')
                    LIMIT 1
                    """,
                    (company_normalized, resolved_domain),
                ).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            query = session.query(Company).filter(Company.company_normalized == company_normalized)
            if resolved_domain:
                query = query.filter(Company.resolved_domain == resolved_domain)
            else:
                query = query.filter((Company.resolved_domain == None) | (Company.resolved_domain == ""))
            company = query.first()
            if company is None:
                return None
            return {
                "company_key": company.company_key,
                "company_display": company.company_display,
                "company_normalized": company.company_normalized,
                "company_root": company.company_root,
                "resolved_domain": company.resolved_domain,
            }

    def find_unique_by_normalized(self, company_normalized: str) -> Optional[Dict[str, Any]]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                rows = conn.execute(
                    """
                    SELECT company_key, company_display, company_normalized, company_root, resolved_domain
                    FROM companies
                    WHERE company_normalized = ?
                    ORDER BY company_key ASC
                    LIMIT 2
                    """,
                    (company_normalized,),
                ).fetchall()
                return dict(rows[0]) if len(rows) == 1 else None
            finally:
                conn.close()

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            rows = (
                session.query(Company)
                .filter(Company.company_normalized == company_normalized)
                .order_by(Company.company_key.asc())
                .limit(2)
                .all()
            )
            if len(rows) != 1:
                return None
            company = rows[0]
            return {
                "company_key": company.company_key,
                "company_display": company.company_display,
                "company_normalized": company.company_normalized,
                "company_root": company.company_root,
                "resolved_domain": company.resolved_domain,
            }

    def find_by_domain(self, resolved_domain: str) -> Optional[Dict[str, Any]]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                row = conn.execute(
                    """
                    SELECT company_key, company_display, company_normalized, company_root, resolved_domain
                    FROM companies
                    WHERE resolved_domain = ?
                    LIMIT 1
                    """,
                    (resolved_domain,),
                ).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            company = (
                session.query(Company)
                .filter(Company.resolved_domain == resolved_domain)
                .first()
            )
            if company is None:
                return None
            return {
                "company_key": company.company_key,
                "company_display": company.company_display,
                "company_normalized": company.company_normalized,
                "company_root": company.company_root,
                "resolved_domain": company.resolved_domain,
            }

    def list_companies(self) -> List[Dict[str, Any]]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM companies
                    ORDER BY company_display ASC, company_key ASC
                    """
                ).fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            rows = (
                session.query(Company)
                .order_by(Company.company_display.asc(), Company.company_key.asc())
                .all()
            )
            return [
                {
                    column.name: getattr(company, column.name)
                    for column in Company.__table__.columns
                }
                for company in rows
            ]


class CompanyAliasRepository(RepositoryBase):
    def replace_aliases(self, companies: List[Dict[str, Any]]) -> None:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                company_keys = [c.get("company_key") for c in companies if c.get("company_key")]
                if company_keys:
                    placeholders = ",".join("?" for _ in company_keys)
                    conn.execute(
                        f"DELETE FROM company_aliases WHERE company_key IN ({placeholders})",
                        company_keys,
                    )

                rows = []
                for company in companies:
                    company_key = company.get("company_key")
                    aliases = company.get("aliases", []) or []
                    alias_type_map = company.get("alias_type_map", {}) or {}
                    for alias in aliases:
                        rows.append(
                            (
                                company_key,
                                alias,
                                alias_type_map.get(alias, company.get("company_normalized")),
                                alias_type_map.get(f"{alias}__type", "observed_name"),
                            )
                        )

                if rows:
                    conn.executemany(
                        """
                        INSERT INTO company_aliases (
                            company_key,
                            alias_value,
                            alias_normalized,
                            alias_type
                        )
                        VALUES (?, ?, ?, ?)
                        """,
                        rows,
                    )
                conn.commit()
            finally:
                conn.close()
            return

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            company_keys = [c.get("company_key") for c in companies if c.get("company_key")]
            if company_keys:
                session.query(CompanyAlias).filter(CompanyAlias.company_key.in_(company_keys)).delete(
                    synchronize_session=False
                )

            aliases_to_insert = []
            for company in companies:
                company_key = company.get("company_key")
                aliases = company.get("aliases", []) or []
                alias_type_map = company.get("alias_type_map", {}) or {}
                for alias in aliases:
                    aliases_to_insert.append(
                        CompanyAlias(
                            company_key=str(company_key),
                            alias_value=str(alias),
                            alias_normalized=str(alias_type_map.get(alias, company.get("company_normalized")) or ""),
                            alias_type=str(alias_type_map.get(f"{alias}__type", "observed_name") or "observed_name"),
                        )
                    )

            session.add_all(aliases_to_insert)
            session.commit()

    def find_company_by_alias_normalized(self, alias_normalized: str) -> Optional[Dict[str, Any]]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                row = conn.execute(
                    """
                    SELECT c.company_key, c.company_display, c.company_normalized, c.resolved_domain
                    FROM company_aliases a
                    JOIN companies c ON c.company_key = a.company_key
                    WHERE a.alias_normalized = ?
                    LIMIT 1
                    """,
                    (alias_normalized,),
                ).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            row = (
                session.query(Company)
                .join(CompanyAlias, CompanyAlias.company_key == Company.company_key)
                .filter(CompanyAlias.alias_normalized == alias_normalized)
                .first()
            )
            if row is None:
                return None
            return {
                "company_key": row.company_key,
                "company_display": row.company_display,
                "company_normalized": row.company_normalized,
                "resolved_domain": row.resolved_domain,
            }


class DomainRepository(RepositoryBase):
    def replace_domains(self, companies: List[Dict[str, Any]]) -> None:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                company_keys = [c.get("company_key") for c in companies if c.get("company_key")]
                if company_keys:
                    placeholders = ",".join("?" for _ in company_keys)
                    conn.execute(
                        f"DELETE FROM domains WHERE company_key IN ({placeholders})",
                        company_keys,
                    )

                rows = []
                for company in companies:
                    if company.get("resolved_domain"):
                        rows.append(
                            (
                                company.get("company_key"),
                                company.get("resolved_domain"),
                                company.get("domain_source"),
                                company.get("domain_confidence"),
                                1,
                            )
                        )

                if rows:
                    conn.executemany(
                        """
                        INSERT INTO domains (
                            company_key,
                            domain,
                            source,
                            confidence,
                            is_primary
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        rows,
                    )
                conn.commit()
            finally:
                conn.close()
            return

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            company_keys = [c.get("company_key") for c in companies if c.get("company_key")]
            if company_keys:
                session.query(Domain).filter(Domain.company_key.in_(company_keys)).delete(
                    synchronize_session=False
                )

            domains_to_insert = []
            for company in companies:
                if company.get("resolved_domain"):
                    domains_to_insert.append(
                        Domain(
                            company_key=str(company.get("company_key")),
                            domain=str(company.get("resolved_domain")),
                            source=company.get("domain_source"),
                            confidence=company.get("domain_confidence"),
                            is_primary=1,
                        )
                    )

            session.add_all(domains_to_insert)
            session.commit()


class CompanyMergeCandidateRepository(RepositoryBase):
    def replace_merge_candidates(self, run_id: str, candidates: List[Dict[str, Any]]) -> None:
        if self.persistence.backend != "sqlite":
            self._replace_merge_candidates_orm(run_id, candidates)
            return

        conn = self.connection()
        try:
            conn.execute("DELETE FROM company_merge_candidates WHERE run_id = ?", (run_id,))
            if candidates:
                conn.executemany(
                    """
                    INSERT INTO company_merge_candidates (
                        run_id,
                        company_key_left,
                        company_key_right,
                        reason,
                        confidence
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            run_id,
                            candidate.get("company_key_left"),
                            candidate.get("company_key_right"),
                            candidate.get("reason"),
                            candidate.get("confidence"),
                        )
                        for candidate in candidates
                    ],
                )
            conn.commit()
        finally:
            conn.close()

    def _replace_merge_candidates_orm(self, run_id: str, candidates: List[Dict[str, Any]]) -> None:
        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            session.query(CompanyMergeCandidate).filter(
                CompanyMergeCandidate.run_id == run_id
            ).delete()
            session.add_all(
                [
                    CompanyMergeCandidate(
                        run_id=run_id,
                        company_key_left=str(candidate.get("company_key_left") or ""),
                        company_key_right=str(candidate.get("company_key_right") or ""),
                        reason=str(candidate.get("reason") or ""),
                        confidence=float(candidate.get("confidence", 0.0) or 0.0),
                    )
                    for candidate in candidates
                ]
            )
            session.commit()


class JobRepository(RepositoryBase):
    def _build_job_fingerprint(self, job: Dict[str, Any]) -> str:
        job_url = (job.get("job_url") or "").strip().lower()
        apply_url = (job.get("apply_url") or "").strip().lower()
        title = (job.get("title") or "").strip().lower()
        company = (job.get("company") or "").strip().lower()
        location = (job.get("location") or "").strip().lower()
        description = (job.get("description") or "").strip().lower()

        if job_url:
            raw = f"job_url|{job_url}"
        elif apply_url:
            raw = f"apply_url|{apply_url}"
        else:
            raw = "|".join(
                [
                    "job_fallback",
                    title,
                    company,
                    location,
                    description,
                ]
            )
        return f"jobfp_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:20]}"

    def _build_job_key(self, job: Dict[str, Any], run_id: str) -> str:
        fingerprint = self._build_job_fingerprint(job)
        raw = f"{run_id}|{fingerprint}"
        return f"job_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:20]}"

    def replace_jobs(self, run_id: str, run_date: str, jobs: List[Dict[str, Any]]) -> None:
        if self.persistence.backend != "sqlite":
            self._replace_jobs_orm(run_id, run_date, jobs)
            return

        conn = self.connection()
        try:
            conn.execute("DELETE FROM jobs WHERE run_id = ?", (run_id,))
            rows = [
                (
                    self._build_job_key(job, run_id),
                    self._build_job_fingerprint(job),
                    run_id,
                    run_date,
                    job.get("title"),
                    job.get("company"),
                    job.get("company_key"),
                    job.get("location"),
                    job.get("job_url"),
                    job.get("apply_url"),
                    job.get("description"),
                    job.get("source"),
                    job.get("detected_at"),
                    1 if job.get("is_remote") else 0,
                    1 if job.get("is_contractor") else 0,
                    1 if job.get("is_full_time") else 0,
                    1 if job.get("nearshore_friendly") else 0,
                    1 if job.get("us_only") else 0,
                    1 if job.get("remote_flag") else 0,
                    1 if job.get("contractor_flag") else 0,
                    1 if job.get("many_openings_signal") else 0,
                    1 if job.get("offshore_mentioned") else 0,
                    int(job.get("urgency_hits") or 0),
                )
                for job in jobs
            ]
            if rows:
                conn.executemany(
                    """
                    INSERT INTO jobs (
                        job_key,
                        job_fingerprint,
                        run_id,
                        run_date,
                        title,
                        company,
                        company_key,
                        location,
                        job_url,
                        apply_url,
                        description,
                        source,
                        detected_at,
                        is_remote,
                        is_contractor,
                        is_full_time,
                        nearshore_friendly,
                        us_only,
                        remote_flag,
                        contractor_flag,
                        many_openings_signal,
                        offshore_mentioned,
                        urgency_hits
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
            conn.commit()
        finally:
            conn.close()

    def _replace_jobs_orm(self, run_id: str, run_date: str, jobs: List[Dict[str, Any]]) -> None:
        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            session.query(Job).filter(Job.run_id == run_id).delete()
            session.add_all(
                [
                    Job(
                        job_key=self._build_job_key(job, run_id),
                        job_fingerprint=self._build_job_fingerprint(job),
                        run_id=run_id,
                        run_date=run_date,
                        title=job.get("title"),
                        company=job.get("company"),
                        company_key=job.get("company_key"),
                        location=job.get("location"),
                        job_url=job.get("job_url"),
                        apply_url=job.get("apply_url"),
                        description=job.get("description"),
                        source=job.get("source"),
                        detected_at=job.get("detected_at"),
                        is_remote=1 if job.get("is_remote") else 0,
                        is_contractor=1 if job.get("is_contractor") else 0,
                        is_full_time=1 if job.get("is_full_time") else 0,
                        nearshore_friendly=1 if job.get("nearshore_friendly") else 0,
                        us_only=1 if job.get("us_only") else 0,
                        remote_flag=1 if job.get("remote_flag") else 0,
                        contractor_flag=1 if job.get("contractor_flag") else 0,
                        many_openings_signal=1 if job.get("many_openings_signal") else 0,
                        offshore_mentioned=1 if job.get("offshore_mentioned") else 0,
                        urgency_hits=int(job.get("urgency_hits") or 0),
                    )
                    for job in jobs
                ]
            )
            session.commit()

    def list_jobs_by_run(self, run_id: str) -> List[Dict[str, Any]]:
        conn = self.connection()
        try:
            rows = conn.execute(
                """
                SELECT *
                FROM jobs
                WHERE run_id = ?
                ORDER BY job_key ASC
                """,
                (run_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()


class LeadRepository(RepositoryBase):
    def _build_lead_fingerprint(self, lead: Dict[str, Any]) -> str:
        company_key = (lead.get("company_key") or "").strip().lower()
        email = (lead.get("email") or "").strip().lower()
        linkedin_url = (lead.get("linkedin_url") or "").strip().lower()
        contact_name = (lead.get("contact_name") or "").strip().lower()
        contact_title = (lead.get("contact_title") or "").strip().lower()

        if email:
            raw = "|".join(
                [
                    company_key,
                    "email",
                    email,
                ]
            )
        elif linkedin_url:
            raw = "|".join(
                [
                    company_key,
                    "linkedin",
                    linkedin_url,
                ]
            )
        else:
            raw = "|".join(
                [
                    company_key,
                    contact_name,
                    contact_title,
                ]
            )

        return f"leadfp_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:20]}"

    def _build_lead_key(self, lead: Dict[str, Any], run_id: str) -> str:
        fingerprint = self._build_lead_fingerprint(lead)
        raw = f"{run_id}|{fingerprint}"
        return f"lead_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:20]}"

    def replace_leads(self, run_id: str, run_date: str, leads: List[Dict[str, Any]]) -> None:
        if self.persistence.backend != "sqlite":
            self._replace_leads_orm(run_id, run_date, leads)
            return

        conn = self.connection()
        try:
            conn.execute("DELETE FROM leads WHERE run_id = ?", (run_id,))
            def _clean(value):
                return (value or "").strip()

            def _clean_email(value):
                return (value or "").strip().lower()

            rows = [
                (
                    self._build_lead_key(lead, run_id),
                    self._build_lead_fingerprint(lead),
                    run_id,
                    run_date,
                    _clean(lead.get("company_key")),
                    _clean(lead.get("contact_name")),
                    _clean(lead.get("contact_title")),
                    _clean_email(lead.get("email")),
                    _clean(lead.get("linkedin_url")),
                    _clean(lead.get("lead_source")),
                    float(lead.get("lead_confidence") or 0),
                    int(lead.get("email_quality_score") or 0),
                    _clean(lead.get("lead_capture_reason")),
                    float(lead.get("lead_relevance_score") or 0),
                    _clean(lead.get("lead_priority_label")),
                    float(lead.get("lead_decision_maker_score") or 0),
                    float(lead.get("lead_icp_fit_score") or 0),
                    float(lead.get("lead_contact_completeness_score") or 0),
                    float(lead.get("lead_penalty_negative_title") or 0),
                    _clean(lead.get("lead_score_reason")),
                    _clean(lead.get("lead_scoring_provider")),
                    _clean(lead.get("lead_scoring_model")),
                    _clean(lead.get("lead_scoring_mode")),
                    float(lead.get("lead_score_title") or 0),
                    float(lead.get("lead_score_source") or 0),
                    float(lead.get("lead_score_email") or 0),
                    float(lead.get("lead_score_linkedin") or 0),
                    float(lead.get("lead_score_email_quality") or 0),
                    float(lead.get("lead_score_confidence") or 0),
                    float(lead.get("lead_score_completeness_penalty") or 0),
                    float(lead.get("lead_score_company_penalty") or 0),
                    _clean(lead.get("target_persona")),
                    _clean(lead.get("suggested_titles")),
                    _clean(lead.get("search_reason")),
                    _clean(lead.get("pain_alignment")),
                    _clean(lead.get("priority")),
                    _clean(lead.get("recommended_channel")),
                    _clean(lead.get("lead_role_type")),
                    _clean(lead.get("why_selected")),
                    _clean(lead.get("outreach_angle")),
                    _clean(lead.get("expected_relevance")),
                    _clean(lead.get("risk_or_uncertainty")),
                )
                for lead in leads
            ]
            if rows:
                conn.executemany(
                    """
                    INSERT INTO leads (
                        lead_key,
                        lead_fingerprint,
                        run_id,
                        run_date,
                        company_key,
                        contact_name,
                        contact_title,
                        email,
                        linkedin_url,
                        lead_source,
                        lead_confidence,
                        email_quality_score,
                        lead_capture_reason,
                        lead_relevance_score,
                        lead_priority_label,
                        lead_decision_maker_score,
                        lead_icp_fit_score,
                        lead_contact_completeness_score,
                        lead_penalty_negative_title,
                        lead_score_reason,
                        lead_scoring_provider,
                        lead_scoring_model,
                        lead_scoring_mode,
                        lead_score_title,
                        lead_score_source,
                        lead_score_email,
                        lead_score_linkedin,
                        lead_score_email_quality,
                        lead_score_confidence,
                        lead_score_completeness_penalty,
                        lead_score_company_penalty,
                        target_persona,
                        suggested_titles,
                        search_reason,
                        pain_alignment,
                        priority,
                        recommended_channel,
                        lead_role_type,
                        why_selected,
                        outreach_angle,
                        expected_relevance,
                        risk_or_uncertainty
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
            conn.commit()
        finally:
            conn.close()

    def _clean_lead_value(self, value: Any) -> str:
        return (value or "").strip()

    def _clean_lead_email(self, value: Any) -> str:
        return (value or "").strip().lower()

    def _replace_leads_orm(self, run_id: str, run_date: str, leads: List[Dict[str, Any]]) -> None:
        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            session.query(Lead).filter(Lead.run_id == run_id).delete()
            session.add_all(
                [
                    Lead(
                        lead_key=self._build_lead_key(lead, run_id),
                        lead_fingerprint=self._build_lead_fingerprint(lead),
                        run_id=run_id,
                        run_date=run_date,
                        company_key=self._clean_lead_value(lead.get("company_key")),
                        contact_name=self._clean_lead_value(lead.get("contact_name")),
                        contact_title=self._clean_lead_value(lead.get("contact_title")),
                        email=self._clean_lead_email(lead.get("email")),
                        linkedin_url=self._clean_lead_value(lead.get("linkedin_url")),
                        lead_source=self._clean_lead_value(lead.get("lead_source")),
                        lead_confidence=float(lead.get("lead_confidence") or 0),
                        email_quality_score=int(lead.get("email_quality_score") or 0),
                        lead_capture_reason=self._clean_lead_value(lead.get("lead_capture_reason")),
                        lead_relevance_score=float(lead.get("lead_relevance_score") or 0),
                        lead_priority_label=self._clean_lead_value(lead.get("lead_priority_label")),
                        lead_decision_maker_score=float(lead.get("lead_decision_maker_score") or 0),
                        lead_icp_fit_score=float(lead.get("lead_icp_fit_score") or 0),
                        lead_contact_completeness_score=float(lead.get("lead_contact_completeness_score") or 0),
                        lead_penalty_negative_title=float(lead.get("lead_penalty_negative_title") or 0),
                        lead_score_reason=self._clean_lead_value(lead.get("lead_score_reason")),
                        lead_scoring_provider=self._clean_lead_value(lead.get("lead_scoring_provider")),
                        lead_scoring_model=self._clean_lead_value(lead.get("lead_scoring_model")),
                        lead_scoring_mode=self._clean_lead_value(lead.get("lead_scoring_mode")),
                        lead_score_title=float(lead.get("lead_score_title") or 0),
                        lead_score_source=float(lead.get("lead_score_source") or 0),
                        lead_score_email=float(lead.get("lead_score_email") or 0),
                        lead_score_linkedin=float(lead.get("lead_score_linkedin") or 0),
                        lead_score_email_quality=float(lead.get("lead_score_email_quality") or 0),
                        lead_score_confidence=float(lead.get("lead_score_confidence") or 0),
                        lead_score_completeness_penalty=float(lead.get("lead_score_completeness_penalty") or 0),
                        lead_score_company_penalty=float(lead.get("lead_score_company_penalty") or 0),
                        target_persona=self._clean_lead_value(lead.get("target_persona")),
                        suggested_titles=self._clean_lead_value(lead.get("suggested_titles")),
                        search_reason=self._clean_lead_value(lead.get("search_reason")),
                        pain_alignment=self._clean_lead_value(lead.get("pain_alignment")),
                        priority=self._clean_lead_value(lead.get("priority")),
                        recommended_channel=self._clean_lead_value(lead.get("recommended_channel")),
                        lead_role_type=self._clean_lead_value(lead.get("lead_role_type")),
                        why_selected=self._clean_lead_value(lead.get("why_selected")),
                        outreach_angle=self._clean_lead_value(lead.get("outreach_angle")),
                        expected_relevance=self._clean_lead_value(lead.get("expected_relevance")),
                        risk_or_uncertainty=self._clean_lead_value(lead.get("risk_or_uncertainty")),
                    )
                    for lead in leads
                ]
            )
            session.commit()

    def list_leads_by_run(self, run_id: str) -> List[Dict[str, Any]]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM leads
                    WHERE run_id = ?
                    ORDER BY rowid ASC
                    """,
                    (run_id,),
                ).fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            rows = (
                session.query(Lead)
                .filter(Lead.run_id == run_id)
                .order_by(Lead.lead_key.asc())
                .all()
            )
            return [
                {
                    column.name: getattr(lead, column.name)
                    for column in Lead.__table__.columns
                }
                for lead in rows
            ]


class CompanyScoreRepository(RepositoryBase):
    def replace_company_scores(self, run_id: str, companies: List[Dict[str, Any]]) -> None:
        if self.persistence.backend != "sqlite":
            self._replace_company_scores_orm(run_id, companies)
            return

        conn = self.connection()
        try:
            conn.execute("DELETE FROM company_scores WHERE run_id = ?", (run_id,))
            rows = [
                (
                    run_id,
                    company.get("company_key"),
                    company.get("opportunity_score"),
                    company.get("opportunity_label"),
                    company.get("icp_bucket"),
                    company.get("commercial_bucket"),
                    company.get("pain_urgency"),
                    company.get("recommended_service"),
                    company.get("reason"),
                    company.get("score_openings"),
                    company.get("score_remote"),
                    company.get("score_contractor"),
                    company.get("score_multi_source"),
                    company.get("score_company_type"),
                    company.get("score_icp_fit"),
                    company.get("score_pain_urgency"),
                    company.get("score_region_fit"),
                    company.get("score_company_scale"),
                    company.get("score_role_seniority_mix"),
                    company.get("score_penalty_competitor"),
                    company.get("score_penalty_negative_signals"),
                    company.get("primary_service_fit"),
                    company.get("buyer_persona_fit"),
                    company.get("opportunity_score_reason"),
                    company.get("scoring_provider"),
                    company.get("scoring_model"),
                    company.get("scoring_mode"),
                )
                for company in companies
                if company.get("company_key")
            ]
            if rows:
                conn.executemany(
                    """
                    INSERT INTO company_scores (
                        run_id,
                        company_key,
                        opportunity_score,
                        opportunity_label,
                        icp_bucket,
                        commercial_bucket,
                        pain_urgency,
                        recommended_service,
                        reason,
                        score_openings,
                        score_remote,
                        score_contractor,
                        score_multi_source,
                        score_company_type,
                        score_icp_fit,
                        score_pain_urgency,
                        score_region_fit,
                        score_company_scale,
                        score_role_seniority_mix,
                        score_penalty_competitor,
                        score_penalty_negative_signals,
                        primary_service_fit,
                        buyer_persona_fit,
                        opportunity_score_reason,
                        scoring_provider,
                        scoring_model,
                        scoring_mode
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
            conn.commit()
        finally:
            conn.close()

    def _replace_company_scores_orm(self, run_id: str, companies: List[Dict[str, Any]]) -> None:
        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            session.query(CompanyScore).filter(CompanyScore.run_id == run_id).delete()
            session.add_all(
                [
                    CompanyScore(
                        run_id=run_id,
                        company_key=str(company.get("company_key") or ""),
                        opportunity_score=company.get("opportunity_score"),
                        opportunity_label=company.get("opportunity_label"),
                        icp_bucket=company.get("icp_bucket"),
                        commercial_bucket=company.get("commercial_bucket"),
                        pain_urgency=company.get("pain_urgency"),
                        recommended_service=company.get("recommended_service"),
                        reason=company.get("reason"),
                        score_openings=company.get("score_openings"),
                        score_remote=company.get("score_remote"),
                        score_contractor=company.get("score_contractor"),
                        score_multi_source=company.get("score_multi_source"),
                        score_company_type=company.get("score_company_type"),
                        score_icp_fit=company.get("score_icp_fit"),
                        score_pain_urgency=company.get("score_pain_urgency"),
                        score_region_fit=company.get("score_region_fit"),
                        score_company_scale=company.get("score_company_scale"),
                        score_role_seniority_mix=company.get("score_role_seniority_mix"),
                        score_penalty_competitor=company.get("score_penalty_competitor"),
                        score_penalty_negative_signals=company.get("score_penalty_negative_signals"),
                        primary_service_fit=company.get("primary_service_fit"),
                        buyer_persona_fit=company.get("buyer_persona_fit"),
                        opportunity_score_reason=company.get("opportunity_score_reason"),
                        scoring_provider=company.get("scoring_provider"),
                        scoring_model=company.get("scoring_model"),
                        scoring_mode=company.get("scoring_mode"),
                    )
                    for company in companies
                    if company.get("company_key")
                ]
            )
            session.commit()
