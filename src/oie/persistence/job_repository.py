from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from sqlalchemy import func

from oie.persistence.models import Company, Job
from oie.persistence.repository_base import RepositoryBase
from oie.persistence.session import create_session_factory


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

