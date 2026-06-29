from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from oie.persistence.models import Lead
from oie.persistence.repository_base import RepositoryBase
from oie.persistence.session import create_session_factory


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

