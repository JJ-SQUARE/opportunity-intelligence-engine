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


class ProviderEventRepository:
    def __init__(self, db_path: str = "data/oie.db") -> None:
        self.db_path = db_path

    def replace_events(self, run_id: str, provider_events: List[Dict[str, Any]]) -> None:
        conn = get_connection(self.db_path)
        try:
            conn.execute("DELETE FROM provider_events WHERE run_id = ?", (run_id,))
            conn.executemany(
                """
                INSERT INTO provider_events (run_id, provider, event_type, message, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        event.get("provider"),
                        event.get("event_type"),
                        event.get("message"),
                        json.dumps(event.get("metadata", {}), ensure_ascii=False),
                    )
                    for event in provider_events
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(company_key) DO UPDATE SET
                    company_display = excluded.company_display,
                    company_normalized = excluded.company_normalized,
                    resolved_domain = excluded.resolved_domain,
                    domain_source = excluded.domain_source,
                    domain_confidence = excluded.domain_confidence,
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

    def _build_job_key(self, job: Dict[str, Any], run_id: str) -> str:
        job_url = (job.get("job_url") or "").strip()
        apply_url = (job.get("apply_url") or "").strip()
        if job_url:
            raw = f"{run_id}|job_url|{job_url}"
        elif apply_url:
            raw = f"{run_id}|apply_url|{apply_url}"
        else:
            raw = "|".join(
                [
                    run_id,
                    (job.get("title") or "").strip().lower(),
                    (job.get("company") or "").strip().lower(),
                    (job.get("description") or "").strip().lower(),
                ]
            )
        return f"job_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:20]}"

    def replace_jobs(self, run_id: str, run_date: str, jobs: List[Dict[str, Any]]) -> None:
        conn = get_connection(self.db_path)
        try:
            conn.execute("DELETE FROM jobs WHERE run_id = ?", (run_id,))
            rows = [
                (
                    self._build_job_key(job, run_id),
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
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
            conn.commit()
        finally:
            conn.close()


class LeadRepository:
    def __init__(self, db_path: str = "data/oie.db") -> None:
        self.db_path = db_path

    def _build_lead_key(self, lead: Dict[str, Any], run_id: str) -> str:
        company_key = (lead.get("company_key") or "").strip()
        email = (lead.get("email") or "").strip().lower()
        linkedin_url = (lead.get("linkedin_url") or "").strip().lower()
        contact_name = (lead.get("contact_name") or "").strip().lower()
        contact_title = (lead.get("contact_title") or "").strip().lower()

        if email:
            raw = "|".join(
                [
                    run_id,
                    company_key,
                    "email",
                    email,
                ]
            )
        elif linkedin_url:
            raw = "|".join(
                [
                    run_id,
                    company_key,
                    "linkedin",
                    linkedin_url,
                ]
            )
        else:
            raw = "|".join(
                [
                    run_id,
                    company_key,
                    contact_name,
                    contact_title,
                ]
            )

        return f"lead_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:20]}"

    def replace_leads(self, run_id: str, run_date: str, leads: List[Dict[str, Any]]) -> None:
        conn = get_connection(self.db_path)
        try:
            conn.execute("DELETE FROM leads WHERE run_id = ?", (run_id,))
            rows = [
                (
                    self._build_lead_key(lead, run_id),
                    run_id,
                    run_date,
                    lead.get("company_key"),
                    lead.get("contact_name"),
                    lead.get("contact_title"),
                    lead.get("email"),
                    lead.get("linkedin_url"),
                    lead.get("lead_source"),
                    lead.get("lead_confidence"),
                )
                for lead in leads
            ]
            if rows:
                conn.executemany(
                    """
                    INSERT INTO leads (
                        lead_key,
                        run_id,
                        run_date,
                        company_key,
                        contact_name,
                        contact_title,
                        email,
                        linkedin_url,
                        lead_source,
                        lead_confidence
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
            conn.commit()
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
