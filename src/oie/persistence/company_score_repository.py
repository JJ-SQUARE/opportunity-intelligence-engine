from __future__ import annotations

from typing import Any, Dict, List

from oie.persistence.models import CompanyScore
from oie.persistence.repository_base import RepositoryBase
from oie.persistence.session import create_session_factory


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

