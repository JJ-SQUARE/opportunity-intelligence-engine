from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


CLASSIFICATION_WEIGHTS = {
    "end_client": 20,
    "consulting": 10,
    "staffing": 5,
    "marketplace": 0,
    "job_board": -10,
    "unknown": 0,
    "": 0,
}


class OpportunityScoringService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def _score_company(self, company: Dict[str, Any]) -> Dict[str, Any]:
        total_openings = int(company.get("total_openings", 0) or 0)
        remote_jobs = int(company.get("remote_jobs", 0) or 0)
        contractor_jobs = int(company.get("contractor_jobs", 0) or 0)
        multi_source_signal = bool(company.get("multi_source_signal", False))
        company_type = (company.get("company_type_ai") or "").strip()

        score_openings = min(total_openings * 8, 40)
        score_remote = min(remote_jobs * 4, 20)
        score_contractor = min(contractor_jobs * 6, 20)
        score_multi_source = 10 if multi_source_signal else 0
        score_company_type = CLASSIFICATION_WEIGHTS.get(company_type, 0)

        total_score = (
            score_openings
            + score_remote
            + score_contractor
            + score_multi_source
            + score_company_type
        )

        return {
            "score_openings": score_openings,
            "score_remote": score_remote,
            "score_contractor": score_contractor,
            "score_multi_source": score_multi_source,
            "score_company_type": score_company_type,
            "opportunity_score": total_score,
        }

    def score_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        scored: List[Dict[str, Any]] = []

        for company in companies:
            score_components = self._score_company(company)

            enriched = dict(company)
            enriched.update(score_components)
            scored.append(enriched)

        scored.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)

        self.ctx.metrics["companies_scored"] = len(scored)
        self.ctx.metrics["scoring_completed"] = True

        return scored
