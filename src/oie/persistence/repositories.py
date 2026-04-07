from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from oie.persistence.sqlite import get_connection


class RunRepository:
    def __init__(self, db_path: str = "data/oie.db") -> None:
        self.db_path = db_path

    def upsert_run(self, run_id: str, run_date: str, status: str, mode: str) -> None:
        conn = get_connection(self.db_path)
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

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection(self.db_path)
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


class RunMetricsRepository:
    def __init__(self, db_path: str = "data/oie.db") -> None:
        self.db_path = db_path

    def replace_metrics(self, run_id: str, metrics: Dict[str, Any]) -> None:
        conn = get_connection(self.db_path)
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

    def get_metrics(self, run_id: str) -> Dict[str, Any]:
        conn = get_connection(self.db_path)
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


class ProviderEventRepository:
    def __init__(self, db_path: str = "data/oie.db") -> None:
        self.db_path = db_path

    def replace_events(self, run_id: str, provider_events: List[Dict[str, Any]]) -> None:
        conn = get_connection(self.db_path)
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

    def list_by_run(self, run_id: str) -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
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



class ProviderOperationMetricsRepository:
    def __init__(self, db_path: str = "data/oie.db") -> None:
        self.db_path = db_path

    def replace_rows(self, run_id: str, rows: List[Dict[str, Any]]) -> None:
        conn = get_connection(self.db_path)
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
                        errors_execution_error
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        )
                        for row in rows
                    ],
                )
            conn.commit()
        finally:
            conn.close()


class CompanyRepository:
    def __init__(self, db_path: str = "data/oie.db") -> None:
        self.db_path = db_path

    def upsert_companies(self, companies: List[Dict[str, Any]]) -> None:
        conn = get_connection(self.db_path)
        try:
            conn.executemany(
                """
                INSERT INTO companies (
                    company_key,
                    company_display,
                    company_normalized,
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
                    industry,
                    employee_range,
                    linkedin_company_url,
                    company_description,
                    company_size,
                    enriched_at,
                    enrichment_source,
                    company_type_ai,
                    classification_confidence_ai,
                    classification_provider,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(company_key) DO UPDATE SET
                    company_display = excluded.company_display,
                    company_normalized = excluded.company_normalized,
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
                    industry = COALESCE(excluded.industry, companies.industry),
                    employee_range = COALESCE(excluded.employee_range, companies.employee_range),
                    linkedin_company_url = COALESCE(excluded.linkedin_company_url, companies.linkedin_company_url),
                    company_description = COALESCE(excluded.company_description, companies.company_description),
                    company_size = COALESCE(excluded.company_size, companies.company_size),
                    enriched_at = COALESCE(excluded.enriched_at, companies.enriched_at),
                    enrichment_source = COALESCE(excluded.enrichment_source, companies.enrichment_source),
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
                        company.get("industry"),
                        company.get("employee_range"),
                        company.get("linkedin_company_url"),
                        company.get("company_description"),
                        company.get("company_size"),
                        company.get("enriched_at"),
                        company.get("enrichment_source"),
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

    def find_by_normalized_and_domain(self, company_normalized: str, resolved_domain: str | None) -> Optional[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        try:
            row = conn.execute(
                """
                SELECT company_key, company_display, company_normalized, resolved_domain
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

    def find_by_domain(self, resolved_domain: str) -> Optional[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        try:
            row = conn.execute(
                """
                SELECT company_key, company_display, company_normalized, resolved_domain
                FROM companies
                WHERE resolved_domain = ?
                LIMIT 1
                """,
                (resolved_domain,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_companies(self) -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
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


class CompanyAliasRepository:
    def __init__(self, db_path: str = "data/oie.db") -> None:
        self.db_path = db_path

    def replace_aliases(self, companies: List[Dict[str, Any]]) -> None:
        conn = get_connection(self.db_path)
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

    def find_company_by_alias_normalized(self, alias_normalized: str) -> Optional[Dict[str, Any]]:
        conn = get_connection(self.db_path)
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


class DomainRepository:
    def __init__(self, db_path: str = "data/oie.db") -> None:
        self.db_path = db_path

    def replace_domains(self, companies: List[Dict[str, Any]]) -> None:
        conn = get_connection(self.db_path)
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


class CompanyMergeCandidateRepository:
    def __init__(self, db_path: str = "data/oie.db") -> None:
        self.db_path = db_path

    def replace_merge_candidates(self, run_id: str, candidates: List[Dict[str, Any]]) -> None:
        conn = get_connection(self.db_path)
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


class JobRepository:
    def __init__(self, db_path: str = "data/oie.db") -> None:
        self.db_path = db_path

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
        conn = get_connection(self.db_path)
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
                        detected_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
            conn.commit()
        finally:
            conn.close()

    def list_jobs_by_run(self, run_id: str) -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
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


class LeadRepository:
    def __init__(self, db_path: str = "data/oie.db") -> None:
        self.db_path = db_path

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
        conn = get_connection(self.db_path)
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
                        lead_relevance_score
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
            conn.commit()
        finally:
            conn.close()

    def list_leads_by_run(self, run_id: str) -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
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


class CompanyScoreRepository:
    def __init__(self, db_path: str = "data/oie.db") -> None:
        self.db_path = db_path

    def replace_company_scores(self, run_id: str, companies: List[Dict[str, Any]]) -> None:
        conn = get_connection(self.db_path)
        try:
            conn.execute("DELETE FROM company_scores WHERE run_id = ?", (run_id,))
            rows = [
                (
                    run_id,
                    company.get("company_key"),
                    company.get("opportunity_score"),
                    company.get("score_openings"),
                    company.get("score_remote"),
                    company.get("score_contractor"),
                    company.get("score_multi_source"),
                    company.get("score_company_type"),
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
                        score_openings,
                        score_remote,
                        score_contractor,
                        score_multi_source,
                        score_company_type
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
            conn.commit()
        finally:
            conn.close()
