from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from oie.persistence.models import Company, Job, Lead, CompanyScore, CompanyMergeCandidate, CompanyScore
from oie.persistence.session import create_session_factory
from oie.persistence.repository_base import RepositoryBase
from oie.persistence.run_repository import RunRepository
from oie.persistence.run_metrics_repository import RunMetricsRepository
from oie.persistence.provider_event_repository import ProviderEventRepository
from oie.persistence.provider_operation_metrics_repository import ProviderOperationMetricsRepository
from oie.persistence.company_repository import CompanyRepository
from oie.persistence.company_alias_repository import CompanyAliasRepository
from oie.persistence.domain_repository import DomainRepository


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

    def list_company_hiring_history(self) -> List[Dict[str, Any]]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                rows = conn.execute(
                    """
                    SELECT
                        c.company_key,
                        c.company_display,
                        c.resolved_domain,
                        j.run_id,
                        j.run_date,
                        COUNT(DISTINCT j.job_key) AS openings
                    FROM companies c
                    JOIN jobs j
                        ON j.company_key = c.company_key
                    GROUP BY
                        c.company_key,
                        c.company_display,
                        c.resolved_domain,
                        j.run_id,
                        j.run_date
                    ORDER BY
                        c.company_display ASC,
                        j.run_date ASC,
                        j.run_id ASC
                    """
                ).fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            rows = (
                session.query(
                    Company.company_key,
                    Company.company_display,
                    Company.resolved_domain,
                    Job.run_id,
                    Job.run_date,
                    func.count(func.distinct(Job.job_key)).label("openings"),
                )
                .join(Job, Job.company_key == Company.company_key)
                .group_by(
                    Company.company_key,
                    Company.company_display,
                    Company.resolved_domain,
                    Job.run_id,
                    Job.run_date,
                )
                .order_by(
                    Company.company_display.asc(),
                    Job.run_date.asc(),
                    Job.run_id.asc(),
                )
                .all()
            )
            return [dict(row._mapping) for row in rows]

    def list_source_trends(self) -> List[Dict[str, Any]]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                rows = conn.execute(
                    """
                    SELECT
                        source,
                        COUNT(DISTINCT job_key) AS jobs_count,
                        COUNT(DISTINCT company_key) AS companies_count,
                        COUNT(DISTINCT run_id) AS runs_count
                    FROM jobs
                    GROUP BY source
                    ORDER BY jobs_count DESC, companies_count DESC, source ASC
                    """
                ).fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            rows = (
                session.query(
                    Job.source.label("source"),
                    func.count(func.distinct(Job.job_key)).label("jobs_count"),
                    func.count(func.distinct(Job.company_key)).label("companies_count"),
                    func.count(func.distinct(Job.run_id)).label("runs_count"),
                )
                .group_by(Job.source)
                .order_by(
                    func.count(func.distinct(Job.job_key)).desc(),
                    func.count(func.distinct(Job.company_key)).desc(),
                    Job.source.asc(),
                )
                .all()
            )
            return [
                {
                    "source": row.source,
                    "jobs_count": row.jobs_count,
                    "companies_count": row.companies_count,
                    "runs_count": row.runs_count,
                }
                for row in rows
            ]

    def list_location_trends(self) -> List[Dict[str, Any]]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                rows = conn.execute(
                    """
                    SELECT
                        location,
                        COUNT(DISTINCT job_key) AS jobs_count,
                        COUNT(DISTINCT company_key) AS companies_count
                    FROM jobs
                    WHERE COALESCE(location, '') != ''
                    GROUP BY location
                    ORDER BY jobs_count DESC, companies_count DESC, location ASC
                    """
                ).fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            rows = (
                session.query(
                    Job.location.label("location"),
                    func.count(func.distinct(Job.job_key)).label("jobs_count"),
                    func.count(func.distinct(Job.company_key)).label("companies_count"),
                )
                .filter(Job.location != None)
                .filter(Job.location != "")
                .group_by(Job.location)
                .order_by(
                    func.count(func.distinct(Job.job_key)).desc(),
                    func.count(func.distinct(Job.company_key)).desc(),
                    Job.location.asc(),
                )
                .all()
            )
            return [
                {
                    "location": row.location,
                    "jobs_count": row.jobs_count,
                    "companies_count": row.companies_count,
                }
                for row in rows
            ]

    def list_new_companies_by_source(self) -> List[Dict[str, Any]]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                rows = conn.execute(
                    """
                    WITH company_first_source AS (
                        SELECT
                            j.company_key,
                            MIN(j.run_date) AS first_run_date
                        FROM jobs j
                        WHERE j.company_key IS NOT NULL
                        GROUP BY j.company_key
                    ),
                    company_first_source_detail AS (
                        SELECT
                            j.company_key,
                            j.source,
                            j.run_date
                        FROM jobs j
                        JOIN company_first_source cfs
                          ON cfs.company_key = j.company_key
                         AND cfs.first_run_date = j.run_date
                    )
                    SELECT
                        source,
                        COUNT(DISTINCT company_key) AS new_companies_count
                    FROM company_first_source_detail
                    GROUP BY source
                    ORDER BY new_companies_count DESC, source ASC
                    """
                ).fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            first_dates = (
                session.query(
                    Job.company_key.label("company_key"),
                    func.min(Job.run_date).label("first_run_date"),
                )
                .filter(Job.company_key != None)
                .group_by(Job.company_key)
                .subquery()
            )

            rows = (
                session.query(
                    Job.source.label("source"),
                    func.count(func.distinct(Job.company_key)).label("new_companies_count"),
                )
                .join(
                    first_dates,
                    (Job.company_key == first_dates.c.company_key)
                    & (Job.run_date == first_dates.c.first_run_date),
                )
                .group_by(Job.source)
                .order_by(
                    func.count(func.distinct(Job.company_key)).desc(),
                    Job.source.asc(),
                )
                .all()
            )
            return [
                {
                    "source": row.source,
                    "new_companies_count": row.new_companies_count,
                }
                for row in rows
            ]


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
