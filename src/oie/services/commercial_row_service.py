from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.persistence.context import PersistenceContext
from oie.services.commercial_selection_service import CommercialSelectionService
from oie.services.commercial_signal_service import CommercialSignalService


class CommercialRowService:
    """Centraliza la construcción de filas comerciales por run.

    Fuente única prevista para:
    - commercial_pipeline
    - commercial_report
    - executive_summary
    - HubSpot
    - Apollo import
    """

    def __init__(
        self,
        ctx: RunContext,
        persistence: PersistenceContext | None = None,
    ) -> None:
        self.ctx = ctx
        self.persistence = persistence or PersistenceContext.from_run_context(ctx)
        self.db_path = (
            self.persistence.path
            or self.ctx.paths.get("db_path")
            or self.ctx.config.get("database", {}).get("path", "data/oie.db")
        )
        self.commercial_signal_service = CommercialSignalService()
        self.commercial_selection_service = CommercialSelectionService(
            self.commercial_signal_service
        )

    def query_rows(self, query: str, params: tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        conn = self.persistence.connection()
        try:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def safe_text(self, value: Any) -> str:
        return self.commercial_signal_service.safe_text(value)

    def safe_float(self, value: Any, default: float = 0.0) -> float:
        return self.commercial_signal_service.safe_float(value, default)

    def safe_int(self, value: Any, default: int = 0) -> int:
        return self.commercial_signal_service.safe_int(value, default)

    def finalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return self.commercial_signal_service.finalize_row(row)

    def finalize_rows(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        finalized = [self.finalize_row(row) for row in rows]
        finalized.sort(
            key=lambda row: (
                0 if self.safe_text(row.get("commercial_bucket")).lower() == "competitor_watchlist" else 1,
                self.safe_int(row.get("commercial_priority_score")),
                self.safe_float(row.get("opportunity_score")),
                1 if self.safe_text(row.get("domain_validation_status")).lower() in {"accepted", "accepted_ai_validated"} else 0,
                1 if self.safe_text(row.get("best_contact_email")) else 0,
                1 if self.safe_text(row.get("best_contact_linkedin_url")) else 0,
                self.safe_text(row.get("company_display")).lower(),
            ),
            reverse=True,
        )
        return finalized

    def build_commercial_pipeline_rows(self) -> List[Dict[str, Any]]:
        query = """
        WITH ranked_leads AS (
            SELECT
                l.company_key,
                l.contact_name,
                l.contact_title,
                l.email,
                l.linkedin_url,
                l.lead_source,
                l.lead_confidence,
                COALESCE(l.email_quality_score, 0) AS email_quality_score,
                COALESCE(l.lead_capture_reason, '') AS lead_capture_reason,
                COALESCE(l.lead_relevance_score, 0) AS lead_relevance_score,
                COALESCE(l.lead_priority_label, '') AS lead_priority_label,
                COALESCE(l.lead_decision_maker_score, 0) AS lead_decision_maker_score,
                COALESCE(l.lead_icp_fit_score, 0) AS lead_icp_fit_score,
                COALESCE(l.lead_contact_completeness_score, 0) AS lead_contact_completeness_score,
                COALESCE(l.lead_penalty_negative_title, 0) AS lead_penalty_negative_title,
                COALESCE(l.lead_score_reason, '') AS lead_score_reason,
                COALESCE(l.lead_scoring_provider, '') AS lead_scoring_provider,
                COALESCE(l.lead_scoring_model, '') AS lead_scoring_model,
                COALESCE(l.lead_scoring_mode, '') AS lead_scoring_mode,
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
                        COALESCE(l.contact_name, '') ASC
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
        best_leads AS (
            SELECT
                company_key,
                contact_name AS best_contact_name,
                contact_title AS best_contact_title,
                email AS best_contact_email,
                linkedin_url AS best_contact_linkedin_url,
                lead_source AS best_lead_source,
                lead_confidence AS best_lead_confidence,
                lead_relevance_score AS best_lead_relevance_score,
                email_quality_score AS best_email_quality_score,
                lead_capture_reason AS best_lead_capture_reason,
                COALESCE(lead_priority_label, '') AS best_lead_priority_label,
                COALESCE(lead_decision_maker_score, 0) AS best_lead_decision_maker_score,
                COALESCE(lead_icp_fit_score, 0) AS best_lead_icp_fit_score,
                COALESCE(lead_contact_completeness_score, 0) AS best_lead_contact_completeness_score,
                COALESCE(lead_penalty_negative_title, 0) AS best_lead_penalty_negative_title,
                COALESCE(lead_score_reason, '') AS best_lead_score_reason,
                COALESCE(lead_scoring_provider, '') AS best_lead_scoring_provider,
                COALESCE(lead_scoring_model, '') AS best_lead_scoring_model,
                COALESCE(lead_scoring_mode, '') AS best_lead_scoring_mode
            FROM ranked_leads
            WHERE rn = 1
        ),
        run_scores AS (
            SELECT
                cs.company_key,
                cs.opportunity_score,
                cs.opportunity_label,
                cs.score_openings,
                cs.score_remote,
                cs.score_contractor,
                cs.score_multi_source,
                cs.score_company_type,
                cs.score_icp_fit,
                cs.score_pain_urgency,
                cs.score_region_fit,
                cs.score_company_scale,
                cs.score_role_seniority_mix,
                cs.score_penalty_competitor,
                cs.score_penalty_negative_signals,
                cs.primary_service_fit,
                cs.buyer_persona_fit,
                cs.opportunity_score_reason,
                cs.scoring_provider,
                cs.scoring_model,
                cs.scoring_mode
            FROM company_scores cs
            WHERE cs.run_id = ?
        )
        SELECT
            s.company_key,
            COALESCE(c.company_display, '') AS company_display,
            COALESCE(c.company_normalized, '') AS company_normalized,
            COALESCE(c.resolved_domain, '') AS resolved_domain,
            COALESCE(c.domain_source, '') AS domain_source,
            COALESCE(c.domain_confidence, 0) AS domain_confidence,
            COALESCE(c.domain_candidate, '') AS domain_candidate,
            COALESCE(c.domain_validation_status, '') AS domain_validation_status,
            COALESCE(c.domain_review_required, 0) AS domain_review_required,
            COALESCE(c.domain_ai_decision, '') AS domain_ai_decision,
            COALESCE(c.company_type_ai, '') AS company_type_ai,
            COALESCE(c.classification_confidence_ai, 0) AS classification_confidence_ai,
            COALESCE(c.industry, '') AS industry,
            COALESCE(c.employee_range, '') AS employee_range,
            COALESCE(c.company_size, '') AS company_size,
            COALESCE(c.linkedin_company_url, '') AS linkedin_company_url,
            COALESCE(c.company_description, '') AS company_description,
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
            COALESCE(bl.best_contact_name, '') AS best_contact_name,
            COALESCE(bl.best_contact_title, '') AS best_contact_title,
            COALESCE(bl.best_contact_email, '') AS best_contact_email,
            COALESCE(bl.best_contact_linkedin_url, '') AS best_contact_linkedin_url,
            COALESCE(bl.best_lead_source, '') AS best_lead_source,
            COALESCE(bl.best_lead_confidence, 0) AS best_lead_confidence,
            COALESCE(bl.best_lead_relevance_score, 0) AS best_lead_relevance_score,
            COALESCE(bl.best_email_quality_score, 0) AS best_email_quality_score,
            COALESCE(bl.best_lead_capture_reason, '') AS best_lead_capture_reason,
            COALESCE(bl.best_lead_priority_label, '') AS best_lead_priority_label,
            COALESCE(bl.best_lead_decision_maker_score, 0) AS best_lead_decision_maker_score,
            COALESCE(bl.best_lead_icp_fit_score, 0) AS best_lead_icp_fit_score,
            COALESCE(bl.best_lead_contact_completeness_score, 0) AS best_lead_contact_completeness_score,
            COALESCE(bl.best_lead_penalty_negative_title, 0) AS best_lead_penalty_negative_title,
            COALESCE(bl.best_lead_score_reason, '') AS best_lead_score_reason,
            COALESCE(bl.best_lead_scoring_provider, '') AS best_lead_scoring_provider,
            COALESCE(bl.best_lead_scoring_model, '') AS best_lead_scoring_model,
            COALESCE(bl.best_lead_scoring_mode, '') AS best_lead_scoring_mode,
            CASE
                WHEN COALESCE(bl.best_contact_email, '') <> '' THEN 'email'
                WHEN COALESCE(bl.best_contact_linkedin_url, '') <> '' THEN 'linkedin'
                WHEN COALESCE(c.linkedin_company_url, '') <> '' THEN 'company_linkedin'
                WHEN COALESCE(c.resolved_domain, '') <> '' THEN 'website_only'
                ELSE 'no_channel'
            END AS suggested_outreach_channel,
            CASE
                WHEN LOWER(COALESCE(c.company_type_ai, '')) IN ('competitor', 'staffing', 'staffing_agency', 'consulting')
                    OR COALESCE(s.score_penalty_competitor, 0) <= -20
                    THEN 'deprioritized_competitor'
                WHEN COALESCE(c.domain_validation_status, '') = 'review' THEN 'review_domain'
                WHEN COALESCE(c.domain_validation_status, '') NOT IN ('accepted', 'accepted_ai_validated') THEN 'pending_domain'
                WHEN COALESCE(bl.best_contact_email, '') <> '' THEN 'ready_email'
                WHEN COALESCE(bl.best_contact_linkedin_url, '') <> '' THEN 'ready_linkedin'
                WHEN COALESCE(c.linkedin_company_url, '') <> '' OR COALESCE(c.resolved_domain, '') <> '' THEN 'research_needed'
                ELSE 'insufficient_data'
            END AS outreach_status,
            CASE
                WHEN LOWER(COALESCE(c.company_type_ai, '')) IN ('competitor')
                    THEN 'benchmark_competitor'
                WHEN LOWER(COALESCE(c.company_type_ai, '')) IN ('staffing', 'staffing_agency', 'consulting', 'marketplace', 'job_board')
                    THEN 'non_icp'
                WHEN COALESCE(c.company_type_ai, '') IN ('end_client', 'product_company')
                     AND COALESCE(s.opportunity_score, 0) >= 55
                    THEN 'strong_icp'
                WHEN COALESCE(c.company_type_ai, '') IN ('end_client', 'product_company')
                     AND COALESCE(s.opportunity_score, 0) >= 25
                    THEN 'possible_icp'
                WHEN COALESCE(s.opportunity_score, 0) >= 40
                    THEN 'possible_icp'
                ELSE 'weak_icp'
            END AS icp_bucket,
            CASE
                WHEN (
                    COALESCE(c.domain_validation_status, '') = 'accepted'
                    AND COALESCE(c.resolved_domain, '') <> ''
                )
                OR COALESCE(bl.best_contact_email, '') <> ''
                OR COALESCE(bl.best_contact_linkedin_url, '') <> ''
                OR COALESCE(c.linkedin_company_url, '') <> ''
                    THEN 1
                ELSE 0
            END AS reachability_ready,
            CASE
                WHEN LOWER(COALESCE(c.company_type_ai, '')) IN ('competitor', 'staffing', 'staffing_agency', 'consulting')
                    OR COALESCE(s.score_penalty_competitor, 0) <= -20
                    THEN 'competitor_watchlist'
                WHEN COALESCE(c.company_type_ai, '') IN ('end_client', 'product_company')
                     AND COALESCE(s.opportunity_score, 0) >= 55
                    THEN 'icp_target'
                WHEN COALESCE(s.opportunity_score, 0) >= 40
                     OR (
                        COALESCE(c.company_type_ai, '') IN ('end_client', 'product_company')
                        AND COALESCE(s.opportunity_score, 0) >= 25
                     )
                    THEN 'partner_candidate'
                ELSE 'low_fit_noise'
            END AS commercial_bucket,
            MAX(
                0,
                (
                    COALESCE(s.opportunity_score, 0)
                    + CASE WHEN COALESCE(c.domain_validation_status, '') IN ('accepted', 'accepted_ai_validated') THEN 8 ELSE 0 END
                    + CASE WHEN COALESCE(bl.best_contact_email, '') <> '' THEN 10 ELSE 0 END
                    + CASE WHEN COALESCE(bl.best_contact_linkedin_url, '') <> '' THEN 4 ELSE 0 END
                    + CASE WHEN COALESCE(bl.best_email_quality_score, 0) >= 80 THEN 5
                           WHEN COALESCE(bl.best_email_quality_score, 0) >= 50 THEN 2
                           ELSE 0 END
                    + CASE WHEN COALESCE(bl.best_lead_source, '') = 'apollo_people' THEN 4
                           WHEN COALESCE(bl.best_lead_source, '') = 'hunter_domain_search' THEN 2
                           ELSE 0 END
                    + CASE WHEN COALESCE(c.company_type_ai, '') IN ('end_client', 'product_company') THEN 6 ELSE 0 END
                    + CASE WHEN COALESCE(c.linkedin_company_url, '') <> '' THEN 2 ELSE 0 END
                    - CASE WHEN COALESCE(c.domain_validation_status, '') = 'review' THEN 20 ELSE 0 END
                    - CASE WHEN COALESCE(c.domain_validation_status, '') NOT IN ('', 'accepted', 'accepted_ai_validated', 'review') THEN 12 ELSE 0 END
                    - CASE
                        WHEN LOWER(COALESCE(c.company_type_ai, '')) IN ('competitor', 'staffing', 'staffing_agency', 'consulting')
                             THEN 80
                        WHEN COALESCE(s.score_penalty_competitor, 0) <= -20
                             THEN 60
                        ELSE 0
                      END
                    - CASE
                        WHEN (
                            COALESCE(s.opportunity_score, 0) < 30
                            AND COALESCE(c.company_type_ai, '') NOT IN ('end_client', 'product_company')
                        ) THEN 15
                        ELSE 0
                      END
                )
            ) AS commercial_priority_score
        FROM run_scores s
        LEFT JOIN companies c
            ON c.company_key = s.company_key
        LEFT JOIN lead_stats ls
            ON ls.company_key = s.company_key
        LEFT JOIN best_leads bl
            ON bl.company_key = s.company_key
        ORDER BY
            CASE
                WHEN LOWER(COALESCE(c.company_type_ai, '')) IN ('competitor', 'staffing', 'staffing_agency', 'consulting')
                    OR COALESCE(s.score_penalty_competitor, 0) <= -20
                    THEN 0
                WHEN COALESCE(c.company_type_ai, '') IN ('end_client', 'product_company')
                     AND COALESCE(s.opportunity_score, 0) >= 55
                    THEN 3
                WHEN COALESCE(s.opportunity_score, 0) >= 40
                     OR (
                        COALESCE(c.company_type_ai, '') IN ('end_client', 'product_company')
                        AND COALESCE(s.opportunity_score, 0) >= 25
                     )
                    THEN 2
                ELSE 1
            END DESC,
            commercial_priority_score DESC,
            COALESCE(s.opportunity_score, 0) DESC,
            CASE WHEN COALESCE(c.domain_validation_status, '') IN ('accepted', 'accepted_ai_validated') THEN 1 ELSE 0 END DESC,
            CASE WHEN COALESCE(bl.best_contact_email, '') <> '' THEN 1 ELSE 0 END DESC,
            CASE WHEN COALESCE(bl.best_contact_linkedin_url, '') <> '' THEN 1 ELSE 0 END DESC,
            c.company_display ASC
        """
        rows = self.query_rows(query, (self.ctx.run_id, self.ctx.run_id, self.ctx.run_id))
        rows = self.finalize_rows(rows)
        rows = self.recompute_best_commercial_leads(rows)
        return rows

    def clear_best_lead_fields(self, row: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = dict(row)
        cleaned["best_contact_name"] = ""
        cleaned["best_contact_title"] = ""
        cleaned["best_contact_email"] = ""
        cleaned["best_contact_linkedin_url"] = ""
        cleaned["best_lead_source"] = ""
        cleaned["best_lead_confidence"] = 0
        cleaned["best_lead_relevance_score"] = 0
        cleaned["best_email_quality_score"] = 0
        cleaned["best_lead_capture_reason"] = ""
        cleaned["best_lead_priority_label"] = ""
        cleaned["best_lead_decision_maker_score"] = 0
        cleaned["best_lead_icp_fit_score"] = 0
        cleaned["best_lead_contact_completeness_score"] = 0
        cleaned["best_lead_penalty_negative_title"] = 0
        cleaned["best_lead_score_reason"] = ""
        cleaned["best_lead_scoring_provider"] = ""
        cleaned["best_lead_scoring_model"] = ""
        cleaned["best_lead_scoring_mode"] = ""
        return cleaned

    def apply_best_lead_to_row(
        self,
        row: Dict[str, Any],
        best_lead: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        updated = self.clear_best_lead_fields(row)

        if not best_lead:
            return self.finalize_row(updated)

        updated["best_contact_name"] = best_lead.get("contact_name", "")
        updated["best_contact_title"] = best_lead.get("contact_title", "")
        updated["best_contact_email"] = best_lead.get("email", "")
        updated["best_contact_linkedin_url"] = best_lead.get("linkedin_url", "")
        updated["best_lead_source"] = best_lead.get("lead_source", "")
        updated["best_lead_confidence"] = best_lead.get("lead_confidence", 0)
        updated["best_lead_relevance_score"] = best_lead.get("lead_relevance_score", 0)
        updated["best_email_quality_score"] = best_lead.get("email_quality_score", 0)
        updated["best_lead_capture_reason"] = best_lead.get("lead_capture_reason", "")
        updated["best_lead_priority_label"] = best_lead.get("lead_priority_label", "")
        updated["best_lead_decision_maker_score"] = best_lead.get("lead_decision_maker_score", 0)
        updated["best_lead_icp_fit_score"] = best_lead.get("lead_icp_fit_score", 0)
        updated["best_lead_contact_completeness_score"] = best_lead.get("lead_contact_completeness_score", 0)
        updated["best_lead_penalty_negative_title"] = best_lead.get("lead_penalty_negative_title", 0)
        updated["best_lead_score_reason"] = best_lead.get("lead_score_reason", "")
        updated["best_lead_scoring_provider"] = best_lead.get("lead_scoring_provider", "")
        updated["best_lead_scoring_model"] = best_lead.get("lead_scoring_model", "")
        updated["best_lead_scoring_mode"] = best_lead.get("lead_scoring_mode", "")

        return self.finalize_row(updated)

    def build_company_contacts(self, company_key: str) -> List[Dict[str, Any]]:
        query = """
        SELECT
            COALESCE(contact_name, '') AS contact_name,
            COALESCE(contact_title, '') AS contact_title,
            COALESCE(email, '') AS email,
            COALESCE(linkedin_url, '') AS linkedin_url,
            COALESCE(lead_source, '') AS lead_source,
            COALESCE(lead_confidence, 0) AS lead_confidence,
            COALESCE(email_quality_score, 0) AS email_quality_score,
            COALESCE(lead_relevance_score, 0) AS lead_relevance_score
        FROM leads
        WHERE run_id = ? AND company_key = ?
        ORDER BY
            COALESCE(lead_relevance_score, 0) DESC,
            COALESCE(email_quality_score, 0) DESC,
            COALESCE(lead_confidence, 0) DESC,
            contact_name ASC
        """
        return self.query_rows(query, (self.ctx.run_id, company_key))

    def select_contacts(
        self,
        company_key: str,
        *,
        max_contacts: int = 3,
        min_relevance_score: int = 45,
    ) -> List[Dict[str, Any]]:
        normalized_company_key = self.safe_text(company_key)
        contacts = self.build_company_contacts(normalized_company_key) if normalized_company_key else []
        return self.commercial_selection_service.select_contacts(
            company_key=normalized_company_key,
            contacts=contacts,
            max_contacts=max_contacts,
            min_relevance_score=min_relevance_score,
        )

    def recompute_best_commercial_leads(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        recomputed: List[Dict[str, Any]] = []

        for row in rows:
            company_key = self.safe_text(row.get("company_key"))
            contacts = self.build_company_contacts(company_key) if company_key else []
            selected_contacts = self.commercial_selection_service.select_contacts(
                company_key=company_key,
                contacts=contacts,
                max_contacts=1,
                min_relevance_score=45,
            )
            best_lead = selected_contacts[0] if selected_contacts else None
            recomputed.append(self.apply_best_lead_to_row(row, best_lead))

        return recomputed

    def rows_with_selected_contacts(
        self,
        rows: List[Dict[str, Any]],
        *,
        max_contacts: int = 3,
        min_relevance_score: int = 45,
    ) -> List[Dict[str, Any]]:
        contacts_by_company: Dict[str, List[Dict[str, Any]]] = {}

        for row in rows:
            company_key = self.safe_text(row.get("company_key"))
            if not company_key:
                continue
            contacts_by_company[company_key] = self.build_company_contacts(company_key)

        return self.commercial_selection_service.rows_with_selected_contacts(
            rows=rows,
            contacts_by_company=contacts_by_company,
            max_contacts=max_contacts,
            min_relevance_score=min_relevance_score,
        )


