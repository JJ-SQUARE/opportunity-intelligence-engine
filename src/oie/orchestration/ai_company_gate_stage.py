from __future__ import annotations

from typing import Any

from oie.orchestration.company_gate_stage import CompanyGateStage
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem


class AICompanyGateStage(Stage):
    name = "company_analyzer"
    order = 5

    HARD_REJECT_TYPES = {
        "job_board",
        "marketplace",
        "staffing",
        "staffing_agency",
        "confidential",
        "noise",
        "generic",
    }

    def load_input(self) -> list[StageItem]:
        return StageCheckpointManager(CompanyGateStage(self.ctx)).read_output()

    def process_item(self, item: StageItem) -> StageItem:
        company = self._company_from_item(item)
        gated_company = self._apply_ai_gate(company)

        return {
            "id": str(item.get("id") or gated_company.get("company") or "ai_company_gate_company"),
            "value": gated_company,
            "metadata": dict(item.get("metadata") or {}),
        }

    def _company_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("AICompanyGateStage item value must be a company object.")
        return dict(value)

    def _apply_ai_gate(self, company: dict[str, Any]) -> dict[str, Any]:
        record = dict(company)
        gate_type = str(record.get("ai_company_gate_company_type") or "").strip().lower()
        gate_relevance = str(record.get("ai_company_gate_relevance") or "").strip().lower()
        should_advance = record.get("ai_company_gate_should_advance")

        hard_reject = gate_type in self.HARD_REJECT_TYPES
        soft_reject = should_advance is False and gate_relevance not in {"medium", "high"}

        if hard_reject or soft_reject:
            record["company_identity_ai_discarded"] = True
            record["ai_company_gate_status"] = "rejected"
            self.ctx.metrics[f"companies_rejected_by_ai_{gate_type or 'unknown'}"] = (
                int(self.ctx.metrics.get(f"companies_rejected_by_ai_{gate_type or 'unknown'}", 0) or 0) + 1
            )
        else:
            record["ai_company_gate_status"] = "advanced"

        return record
