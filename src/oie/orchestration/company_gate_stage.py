from __future__ import annotations

from typing import Any

from oie.orchestration.job_intelligence_stage import JobIntelligenceStage
from oie.orchestration.stage_base import Stage
from oie.orchestration.stage_checkpoint_manager import StageCheckpointManager
from oie.orchestration.stage_item import StageItem
from oie.services.hiring_signals_service import HiringSignalsService


class CompanyGateStage(Stage):
    name = "domain_gate"
    order = 4

    def load_input(self) -> list[StageItem]:
        return StageCheckpointManager(JobIntelligenceStage(self.ctx)).read_output()

    BLOCKED_COMPANY_TYPES = {
        "confidential", "noise", "job_board", "staffing_agency",
        "marketplace", "competitor",
    }

    def process_item(self, item: StageItem) -> StageItem | None:
        job = self._job_from_item(item)

        # Pre-filtro: respetar decisión de freshness_gate sin reagregar
        should_advance = job.get("ai_company_gate_should_advance")
        company_type = str(job.get("ai_company_gate_company_type") or "").strip().lower()
        relevance = str(job.get("ai_company_gate_relevance") or "").strip().lower()

        if should_advance is False or relevance == "blocked":
            self.ctx.metrics["domain_gate_rejected_by_freshness"] = (
                int(self.ctx.metrics.get("domain_gate_rejected_by_freshness", 0)) + 1
            )
            return None

        if company_type in self.BLOCKED_COMPANY_TYPES:
            self.ctx.metrics["domain_gate_rejected_by_type"] = (
                int(self.ctx.metrics.get("domain_gate_rejected_by_type", 0)) + 1
            )
            return None

        companies = HiringSignalsService(self.ctx).aggregate_by_company([job])
        company = companies[0] if companies else {}

        # Post-filtro: si el agregado decide bloquear, rechazar
        if not company.get("ai_company_gate_should_advance", True):
            self.ctx.metrics["domain_gate_rejected_post_aggregate"] = (
                int(self.ctx.metrics.get("domain_gate_rejected_post_aggregate", 0)) + 1
            )
            return None

        return {
            "id": str(company.get("company") or item.get("id") or "unknown_company"),
            "value": company,
            "metadata": {
                **dict(item.get("metadata") or {}),
                "company": company.get("company"),
            },
        }

    def _job_from_item(self, item: StageItem) -> dict[str, Any]:
        value = item.get("value") or {}
        if not isinstance(value, dict):
            raise TypeError("CompanyGateStage item value must be a job object.")
        return dict(value)
