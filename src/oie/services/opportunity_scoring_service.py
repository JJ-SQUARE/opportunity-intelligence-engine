from __future__ import annotations

from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class OpportunityScoringService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def score_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        scored: List[Dict[str, Any]] = []

        for company in companies:
            total_openings = int(company.get("total_openings", 0) or 0)
            remote_jobs = int(company.get("remote_jobs", 0) or 0)
            contractor_jobs = int(company.get("contractor_jobs", 0) or 0)

            score = 0
            score += min(total_openings * 10, 50)
            score += min(remote_jobs * 5, 20)
            score += min(contractor_jobs * 8, 20)

            enriched = dict(company)
            enriched["opportunity_score"] = score
            scored.append(enriched)

        scored.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)

        self.ctx.metrics["companies_scored"] = len(scored)
        self.ctx.metrics["scoring_completed"] = True

        return scored
