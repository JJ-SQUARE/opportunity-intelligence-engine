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

    def process_item(self, item: StageItem) -> StageItem:
        job = self._job_from_item(item)
        companies = HiringSignalsService(self.ctx).aggregate_by_company([job])
        company = companies[0] if companies else {}

        return {
            "id": str(item.get("id") or company.get("company") or "unknown_company"),
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
