from __future__ import annotations

from typing import Any

from oie.orchestration.opportunity_scoring_stage import OpportunityScoringStage
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem
from oie.services.commercial_selection_service import CommercialSelectionService
from oie.services.commercial_signal_service import CommercialSignalService


class CompanyLimitStage(Stage):
    name = "company_limit"
    order = 11

    def load_input(self) -> list[StageItem]:
        return StageCheckpointManager(OpportunityScoringStage(self.ctx)).read_output()

    def process_item(self, item: StageItem) -> StageItem:
        company = self._company_from_item(item)

        if company.get("company_identity_ai_discarded") is True:
            return {
                "id": str(item.get("id") or company.get("company") or "company_limit_company"),
                "value": company,
                "metadata": dict(item.get("metadata") or {}),
            }

        limited = self._limit_companies([company])
        limited_company = limited[0] if limited else {
            **company,
            "company_limit_excluded": True,
        }

        return {
            "id": str(item.get("id") or limited_company.get("company") or "company_limit_company"),
            "value": limited_company,
            "metadata": dict(item.get("metadata") or {}),
        }

    def _company_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("CompanyLimitStage item value must be a company object.")
        return dict(value)

    def _limit_companies(self, companies: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raw_limit = self.ctx.flags.get("limit")
        commercial_signal_service = CommercialSignalService()
        selection_service = CommercialSelectionService(commercial_signal_service)

        sorted_companies = selection_service.sort_companies(companies)
        actionable_companies = selection_service.commercially_actionable_companies(sorted_companies)

        self.ctx.metrics["companies_commercial_candidates"] = len(actionable_companies)
        self.ctx.metrics["companies_commercial_filtered_out"] = max(
            len(sorted_companies) - len(actionable_companies),
            0,
        )

        selection_pool = sorted_companies
        used_commercial_gate = False
        self.ctx.metrics["companies_limit_used_analytic_fallback"] = bool(sorted_companies)
        self.ctx.metrics["companies_limit_commercial_gate_soft_only"] = True

        if raw_limit in (None, "") or raw_limit is False:
            self.ctx.metrics["companies_limit_requested"] = 0
            self.ctx.metrics["companies_limit_applied"] = len(selection_pool)
            self.ctx.metrics["companies_limit_truncated"] = 0
            self.ctx.metrics["companies_limit_used_commercial_gate"] = used_commercial_gate
            return selection_pool

        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            self.ctx.metrics["companies_limit_invalid"] = True
            self.ctx.metrics["companies_limit_requested"] = 0
            self.ctx.metrics["companies_limit_applied"] = len(selection_pool)
            self.ctx.metrics["companies_limit_truncated"] = 0
            self.ctx.metrics["companies_limit_used_commercial_gate"] = used_commercial_gate
            return selection_pool

        if limit <= 0:
            self.ctx.metrics["companies_limit_requested"] = limit
            self.ctx.metrics["companies_limit_applied"] = 0
            self.ctx.metrics["companies_limit_truncated"] = len(selection_pool)
            self.ctx.metrics["companies_limit_used_commercial_gate"] = used_commercial_gate
            return []

        limited = selection_pool[:limit]
        self.ctx.metrics["companies_limit_requested"] = limit
        self.ctx.metrics["companies_limit_applied"] = len(limited)
        self.ctx.metrics["companies_limit_truncated"] = max(len(selection_pool) - len(limited), 0)
        self.ctx.metrics["companies_limit_used_commercial_gate"] = used_commercial_gate
        return limited
