from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import func

from oie.persistence.models import Company, CompanyScore, Job, Lead
from oie.persistence.repository_base import RepositoryBase
from oie.persistence.session import create_session_factory


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

    def get_company_by_key(self, company_key: str) -> Optional[Dict[str, Any]]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                row = conn.execute(
                    """
                    SELECT *
                    FROM companies
                    WHERE company_key = ?
                    LIMIT 1
                    """,
                    (company_key,),
                ).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            company = session.get(Company, company_key)
            if company is None:
                return None
            return {
                column.name: getattr(company, column.name)
                for column in Company.__table__.columns
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

    def list_opportunity_dataset_by_run(self, run_id: str) -> List[Dict[str, Any]]:
        if self.persistence.backend == "sqlite":
            conn = self.connection()
            try:
                rows = conn.execute(
                    """
                    WITH jobs_agg AS (
                        SELECT
                            j.company_key,
                            COUNT(DISTINCT j.job_key) AS jobs_count,
                            COALESCE(MAX(j.title), '') AS sample_job_title
                        FROM jobs j
                        WHERE j.run_id = ?
                        GROUP BY j.company_key
                    ),
                    scores_agg AS (
                        SELECT
                            cs.company_key,
                            COALESCE(MAX(cs.opportunity_score), 0) AS opportunity_score,
                            COALESCE(MAX(cs.score_openings), 0) AS score_openings,
                            COALESCE(MAX(cs.score_remote), 0) AS score_remote,
                            COALESCE(MAX(cs.score_contractor), 0) AS score_contractor,
                            COALESCE(MAX(cs.score_multi_source), 0) AS score_multi_source,
                            COALESCE(MAX(cs.score_company_type), 0) AS score_company_type,
                            COALESCE(MAX(cs.score_icp_fit), 0) AS score_icp_fit,
                            COALESCE(MAX(cs.score_pain_urgency), 0) AS score_pain_urgency,
                            COALESCE(MAX(cs.score_region_fit), 0) AS score_region_fit,
                            COALESCE(MAX(cs.score_company_scale), 0) AS score_company_scale,
                            COALESCE(MAX(cs.score_role_seniority_mix), 0) AS score_role_seniority_mix,
                            COALESCE(MAX(cs.score_penalty_competitor), 0) AS score_penalty_competitor,
                            COALESCE(MAX(cs.score_penalty_negative_signals), 0) AS score_penalty_negative_signals,
                            COALESCE(MAX(cs.primary_service_fit), '') AS primary_service_fit,
                            COALESCE(MAX(cs.buyer_persona_fit), '') AS buyer_persona_fit,
                            COALESCE(MAX(cs.opportunity_label), '') AS opportunity_label,
                            COALESCE(MAX(cs.opportunity_score_reason), '') AS opportunity_score_reason,
                            COALESCE(MAX(cs.scoring_provider), '') AS scoring_provider,
                            COALESCE(MAX(cs.scoring_model), '') AS scoring_model,
                            COALESCE(MAX(cs.scoring_mode), '') AS scoring_mode
                        FROM company_scores cs
                        WHERE cs.run_id = ?
                        GROUP BY cs.company_key
                    ),
                    ranked_leads AS (
                        SELECT
                            l.company_key,
                            COALESCE(l.contact_name, '') AS contact_name,
                            COALESCE(l.contact_title, '') AS contact_title,
                            COALESCE(l.email, '') AS email,
                            COALESCE(l.linkedin_url, '') AS linkedin_url,
                            COALESCE(l.lead_source, '') AS lead_source,
                            COALESCE(l.lead_confidence, 0) AS lead_confidence,
                            COALESCE(l.email_quality_score, 0) AS email_quality_score,
                            COALESCE(l.lead_capture_reason, '') AS lead_capture_reason,
                            COALESCE(l.lead_relevance_score, 0) AS lead_relevance_score,
                            ROW_NUMBER() OVER (
                                PARTITION BY l.company_key
                                ORDER BY
                                    COALESCE(l.lead_relevance_score, 0) DESC,
                                    COALESCE(l.email_quality_score, 0) DESC,
                                    COALESCE(l.lead_confidence, 0) DESC,
                                    CASE LOWER(COALESCE(l.lead_source, ''))
                                        WHEN 'apollo_people' THEN 3
                                        WHEN 'hunter_domain_search' THEN 2
                                        WHEN 'stub_generation' THEN 1
                                        ELSE 0
                                    END DESC,
                                    CASE WHEN COALESCE(l.linkedin_url, '') <> '' THEN 1 ELSE 0 END DESC,
                                    COALESCE(l.contact_name, '') ASC,
                                    l.lead_key DESC
                            ) AS rn
                        FROM leads l
                        WHERE l.run_id = ?
                    ),
                    lead_stats AS (
                        SELECT
                            l.company_key,
                            COUNT(*) AS lead_count,
                            SUM(CASE WHEN LOWER(COALESCE(l.lead_source, '')) = 'apollo_people' THEN 1 ELSE 0 END) AS apollo_leads_count,
                            SUM(CASE WHEN LOWER(COALESCE(l.lead_source, '')) = 'hunter_domain_search' THEN 1 ELSE 0 END) AS hunter_leads_count,
                            SUM(CASE WHEN COALESCE(l.email, '') <> '' THEN 1 ELSE 0 END) AS contacts_with_email_count,
                            SUM(CASE WHEN COALESCE(l.linkedin_url, '') <> '' THEN 1 ELSE 0 END) AS contacts_with_linkedin_count
                        FROM leads l
                        WHERE l.run_id = ?
                        GROUP BY l.company_key
                    ),
                    best_lead AS (
                        SELECT *
                        FROM ranked_leads
                        WHERE rn = 1
                    )
                    SELECT
                        c.company_key,
                        c.company_display,
                        c.company_normalized,
                        c.resolved_domain,
                        c.domain_source,
                        c.domain_confidence,
                        c.domain_candidate,
                        c.domain_validation_status,
                        c.domain_review_required,
                        c.domain_ai_decision,
                        c.industry,
                        c.employee_range,
                        c.linkedin_company_url,
                        c.company_description,
                        c.company_type_ai,
                        c.classification_confidence_ai,
                        COALESCE(j.sample_job_title, '') AS sample_job_title,
                        COALESCE(j.jobs_count, 0) AS jobs_count,
                        COALESCE(s.opportunity_score, 0) AS opportunity_score,
                        COALESCE(s.opportunity_label, '') AS opportunity_label,
                        COALESCE(s.score_openings, 0) AS score_openings,
                        COALESCE(s.score_remote, 0) AS score_remote,
                        COALESCE(s.score_contractor, 0) AS score_contractor,
                        COALESCE(s.score_multi_source, 0) AS score_multi_source,
                        COALESCE(s.score_company_type, 0) AS score_company_type,
                        COALESCE(s.score_icp_fit, 0) AS score_icp_fit,
                        COALESCE(s.score_pain_urgency, 0) AS score_pain_urgency,
                        COALESCE(s.score_region_fit, 0) AS score_region_fit,
                        COALESCE(s.score_company_scale, 0) AS score_company_scale,
                        COALESCE(s.score_role_seniority_mix, 0) AS score_role_seniority_mix,
                        COALESCE(s.score_penalty_competitor, 0) AS score_penalty_competitor,
                        COALESCE(s.score_penalty_negative_signals, 0) AS score_penalty_negative_signals,
                        COALESCE(s.primary_service_fit, '') AS primary_service_fit,
                        COALESCE(s.buyer_persona_fit, '') AS buyer_persona_fit,
                        COALESCE(s.opportunity_score_reason, '') AS opportunity_score_reason,
                        COALESCE(s.scoring_provider, '') AS scoring_provider,
                        COALESCE(s.scoring_model, '') AS scoring_model,
                        COALESCE(s.scoring_mode, '') AS scoring_mode,
                        COALESCE(ls.lead_count, 0) AS lead_count,
                        COALESCE(ls.apollo_leads_count, 0) AS apollo_leads_count,
                        COALESCE(ls.hunter_leads_count, 0) AS hunter_leads_count,
                        COALESCE(ls.contacts_with_email_count, 0) AS contacts_with_email_count,
                        COALESCE(ls.contacts_with_linkedin_count, 0) AS contacts_with_linkedin_count,
                        COALESCE(bl.contact_name, '') AS contact_name,
                        COALESCE(bl.contact_title, '') AS contact_title,
                        COALESCE(bl.email, '') AS email,
                        COALESCE(bl.linkedin_url, '') AS linkedin_url,
                        COALESCE(bl.lead_source, '') AS lead_source,
                        COALESCE(bl.lead_confidence, 0) AS lead_confidence,
                        COALESCE(bl.email_quality_score, 0) AS email_quality_score,
                        COALESCE(bl.lead_capture_reason, '') AS lead_capture_reason,
                        COALESCE(bl.lead_relevance_score, 0) AS lead_relevance_score
                    FROM companies c
                    LEFT JOIN jobs_agg j ON j.company_key = c.company_key
                    LEFT JOIN scores_agg s ON s.company_key = c.company_key
                    LEFT JOIN lead_stats ls ON ls.company_key = c.company_key
                    LEFT JOIN best_lead bl ON bl.company_key = c.company_key
                    WHERE COALESCE(j.jobs_count, 0) > 0
                    ORDER BY
                        COALESCE(s.opportunity_score, 0) DESC,
                        COALESCE(j.jobs_count, 0) DESC,
                        c.company_display ASC
                    """,
                    (run_id, run_id, run_id, run_id),
                ).fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

        # Conservative fallback for non-SQLite: reuse ORM table reads and compose in Python.
        companies = self.list_companies()
        jobs = JobRepository(persistence=self.persistence).list_jobs_by_run(run_id)
        leads = LeadRepository(persistence=self.persistence).list_leads_by_run(run_id)

        SessionFactory = create_session_factory(self.persistence.settings)
        with SessionFactory() as session:
            scores = (
                session.query(CompanyScore)
                .filter(CompanyScore.run_id == run_id)
                .all()
            )

        jobs_by_company: dict[str, list[dict[str, Any]]] = {}
        for job in jobs:
            company_key = job.get("company_key")
            if company_key:
                jobs_by_company.setdefault(company_key, []).append(job)

        scores_by_company = {score.company_key: score for score in scores}
        leads_by_company: dict[str, list[dict[str, Any]]] = {}
        for lead in leads:
            company_key = lead.get("company_key")
            if company_key:
                leads_by_company.setdefault(company_key, []).append(lead)

        rows: list[dict[str, Any]] = []
        for company in companies:
            company_key = company.get("company_key")
            company_jobs = jobs_by_company.get(company_key, [])
            if not company_jobs:
                continue

            company_leads = leads_by_company.get(company_key, [])
            best_lead = sorted(
                company_leads,
                key=lambda lead: (
                    float(lead.get("lead_relevance_score") or 0),
                    int(lead.get("email_quality_score") or 0),
                    float(lead.get("lead_confidence") or 0),
                    {"apollo_people": 3, "hunter_domain_search": 2, "stub_generation": 1}.get(
                        str(lead.get("lead_source") or "").lower(),
                        0,
                    ),
                    1 if lead.get("linkedin_url") else 0,
                    str(lead.get("contact_name") or ""),
                ),
                reverse=True,
            )
            lead = best_lead[0] if best_lead else {}
            score = scores_by_company.get(company_key)

            row = dict(company)
            row.update(
                {
                    "sample_job_title": max(str(job.get("title") or "") for job in company_jobs),
                    "jobs_count": len({job.get("job_key") for job in company_jobs}),
                    "opportunity_score": getattr(score, "opportunity_score", 0) if score else 0,
                    "opportunity_label": getattr(score, "opportunity_label", "") if score else "",
                    "score_openings": getattr(score, "score_openings", 0) if score else 0,
                    "score_remote": getattr(score, "score_remote", 0) if score else 0,
                    "score_contractor": getattr(score, "score_contractor", 0) if score else 0,
                    "score_multi_source": getattr(score, "score_multi_source", 0) if score else 0,
                    "score_company_type": getattr(score, "score_company_type", 0) if score else 0,
                    "score_icp_fit": getattr(score, "score_icp_fit", 0) if score else 0,
                    "score_pain_urgency": getattr(score, "score_pain_urgency", 0) if score else 0,
                    "score_region_fit": getattr(score, "score_region_fit", 0) if score else 0,
                    "score_company_scale": getattr(score, "score_company_scale", 0) if score else 0,
                    "score_role_seniority_mix": getattr(score, "score_role_seniority_mix", 0) if score else 0,
                    "score_penalty_competitor": getattr(score, "score_penalty_competitor", 0) if score else 0,
                    "score_penalty_negative_signals": getattr(score, "score_penalty_negative_signals", 0) if score else 0,
                    "primary_service_fit": getattr(score, "primary_service_fit", "") if score else "",
                    "buyer_persona_fit": getattr(score, "buyer_persona_fit", "") if score else "",
                    "opportunity_score_reason": getattr(score, "opportunity_score_reason", "") if score else "",
                    "scoring_provider": getattr(score, "scoring_provider", "") if score else "",
                    "scoring_model": getattr(score, "scoring_model", "") if score else "",
                    "scoring_mode": getattr(score, "scoring_mode", "") if score else "",
                    "lead_count": len(company_leads),
                    "apollo_leads_count": sum(1 for item in company_leads if str(item.get("lead_source") or "").lower() == "apollo_people"),
                    "hunter_leads_count": sum(1 for item in company_leads if str(item.get("lead_source") or "").lower() == "hunter_domain_search"),
                    "contacts_with_email_count": sum(1 for item in company_leads if item.get("email")),
                    "contacts_with_linkedin_count": sum(1 for item in company_leads if item.get("linkedin_url")),
                    "contact_name": lead.get("contact_name", ""),
                    "contact_title": lead.get("contact_title", ""),
                    "email": lead.get("email", ""),
                    "linkedin_url": lead.get("linkedin_url", ""),
                    "lead_source": lead.get("lead_source", ""),
                    "lead_confidence": lead.get("lead_confidence", 0),
                    "email_quality_score": lead.get("email_quality_score", 0),
                    "lead_capture_reason": lead.get("lead_capture_reason", ""),
                    "lead_relevance_score": lead.get("lead_relevance_score", 0),
                }
            )
            rows.append(row)

        rows.sort(
            key=lambda row: (
                float(row.get("opportunity_score") or 0),
                int(row.get("jobs_count") or 0),
                str(row.get("company_display") or ""),
            ),
            reverse=True,
        )
        return rows

