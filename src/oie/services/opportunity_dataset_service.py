from __future__ import annotations

import sqlite3
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.services.commercial_selection_service import CommercialSelectionService
from oie.services.commercial_signal_service import CommercialSignalService


class OpportunityDatasetService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.db_path = self.ctx.config.get("database", {}).get("path", "data/oie.db")
        self.commercial_signal_service = CommercialSignalService()
        self.commercial_selection_service = CommercialSelectionService(self.commercial_signal_service)

    def build_dataset(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

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
                                COALESCE(l.lead_source, '') DESC,
                                COALESCE(l.lead_confidence, 0) DESC,
                                CASE LOWER(COALESCE(l.lead_source, ''))
                                    WHEN 'apollo_people' THEN 3
                                    WHEN 'hunter_domain_search' THEN 2
                                    WHEN 'stub_generation' THEN 1
                                    ELSE 0
                                END DESC,
                                CASE WHEN COALESCE(l.linkedin_url, '') <> '' THEN 1 ELSE 0 END DESC,
                                COALESCE(l.contact_name, '') ASC,
                                l.rowid DESC
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
                    SELECT
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
                LEFT JOIN jobs_agg j
                    ON j.company_key = c.company_key
                LEFT JOIN scores_agg s
                    ON s.company_key = c.company_key
                LEFT JOIN lead_stats ls
                    ON ls.company_key = c.company_key
                LEFT JOIN best_lead bl
                    ON bl.company_key = c.company_key
                WHERE COALESCE(j.jobs_count, 0) > 0
                ORDER BY
                    COALESCE(s.opportunity_score, 0) DESC,
                    COALESCE(j.jobs_count, 0) DESC,
                    c.company_display ASC
                """,
                (self.ctx.run_id, self.ctx.run_id, self.ctx.run_id, self.ctx.run_id),
            ).fetchall()
        finally:
            conn.close()

        dataset = []
        for row in rows:
            record = dict(row)
            record = self.commercial_signal_service.finalize_row(record)
            dataset.append(record)

        # =========================
        # FILTRO_COMERCIAL_DATASET (FIX)
        # =========================
        # =========================
        # FILTRO_COMERCIAL_DATASET (REVERT - WRONG LEVEL)
        # =========================
        # NOTA: no filtramos dataset por lead aquí porque:
        # - record es compañía, no lead
        # - rompe coherencia y tests
        # - el filtrado correcto ya ocurre en lead selection

        dataset = self.commercial_selection_service.sort_companies_analytic(dataset)

        self.ctx.metrics["opportunity_dataset_rows"] = len(dataset)
        self.ctx.metrics["opportunity_dataset_reachability_ready"] = sum(
            1 for row in dataset if int(row.get("reachability_ready") or 0) == 1
        )
        self.ctx.metrics["opportunity_dataset_strong_icp"] = sum(
            1 for row in dataset if str(row.get("icp_bucket") or "") == "strong_icp"
        )
        return dataset

    def build_top_opportunities(self, limit: int = 25) -> List[Dict[str, Any]]:
        dataset = self.build_dataset()
        return self.commercial_selection_service.top_companies_analytic(dataset, limit=limit)
