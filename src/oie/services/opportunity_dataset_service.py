from __future__ import annotations

import sqlite3
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class OpportunityDatasetService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.db_path = self.ctx.config.get("database", {}).get("path", "data/oie.db")

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
                        COALESCE(MAX(cs.score_company_type), 0) AS score_company_type
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
                        ROW_NUMBER() OVER (
                            PARTITION BY l.company_key
                            ORDER BY
                                CASE WHEN COALESCE(l.email, '') <> '' THEN 1 ELSE 0 END DESC,
                                CASE LOWER(COALESCE(l.lead_source, ''))
                                    WHEN 'apollo_people' THEN 3
                                    WHEN 'hunter_domain_search' THEN 2
                                    WHEN 'stub_generation' THEN 1
                                    ELSE 0
                                END DESC,
                                COALESCE(l.lead_confidence, 0) DESC,
                                CASE WHEN COALESCE(l.linkedin_url, '') <> '' THEN 1 ELSE 0 END DESC,
                                l.rowid DESC
                        ) AS rn
                    FROM leads l
                    WHERE l.run_id = ?
                ),
                best_lead AS (
                    SELECT
                        company_key,
                        contact_name,
                        contact_title,
                        email,
                        linkedin_url,
                        lead_source,
                        lead_confidence
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
                    COALESCE(s.score_openings, 0) AS score_openings,
                    COALESCE(s.score_remote, 0) AS score_remote,
                    COALESCE(s.score_contractor, 0) AS score_contractor,
                    COALESCE(s.score_multi_source, 0) AS score_multi_source,
                    COALESCE(s.score_company_type, 0) AS score_company_type,
                    COALESCE(bl.contact_name, '') AS contact_name,
                    COALESCE(bl.contact_title, '') AS contact_title,
                    COALESCE(bl.email, '') AS email,
                    COALESCE(bl.linkedin_url, '') AS linkedin_url,
                    COALESCE(bl.lead_source, '') AS lead_source,
                    COALESCE(bl.lead_confidence, 0) AS lead_confidence
                FROM companies c
                LEFT JOIN jobs_agg j
                    ON j.company_key = c.company_key
                LEFT JOIN scores_agg s
                    ON s.company_key = c.company_key
                LEFT JOIN best_lead bl
                    ON bl.company_key = c.company_key
                WHERE COALESCE(j.jobs_count, 0) > 0
                ORDER BY
                    COALESCE(s.opportunity_score, 0) DESC,
                    COALESCE(j.jobs_count, 0) DESC,
                    c.company_display ASC
                """,
                (self.ctx.run_id, self.ctx.run_id, self.ctx.run_id),
            ).fetchall()
        finally:
            conn.close()

        dataset = [dict(row) for row in rows]
        self.ctx.metrics["opportunity_dataset_rows"] = len(dataset)
        return dataset

    def build_top_opportunities(self, limit: int = 25) -> List[Dict[str, Any]]:
        dataset = self.build_dataset()
        return dataset[:limit]
