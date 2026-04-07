from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

from oie.orchestration.run_context import RunContext


OPPORTUNITY_DATASET_HEADERS = [
    "company_key",
    "company_display",
    "company_normalized",
    "resolved_domain",
    "domain_source",
    "domain_confidence",
    "domain_candidate",
    "domain_validation_status",
    "domain_review_required",
    "domain_ai_decision",
    "industry",
    "employee_range",
    "linkedin_company_url",
    "company_description",
    "company_type_ai",
    "classification_confidence_ai",
    "sample_job_title",
    "jobs_count",
    "opportunity_score",
    "score_openings",
    "score_remote",
    "score_contractor",
    "score_multi_source",
    "score_company_type",
    "contact_name",
    "contact_title",
    "email",
    "linkedin_url",
    "lead_source",
    "lead_confidence",
    "email_quality_score",
    "lead_capture_reason",
    "lead_relevance_score",
]


class OpportunityDatasetExportService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def _get_output_dir(self) -> Path:
        output_dir_value = self.ctx.paths.get("output_dir")
        if not output_dir_value:
            base_output = ((self.ctx.config or {}).get("outputs", {}) or {}).get("path") or "data/outputs"
            run_id = self.ctx.run_id or "manual_run"
            output_dir_value = str(Path(base_output) / run_id)
            self.ctx.paths["output_dir"] = output_dir_value

        output_dir = Path(output_dir_value)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _write_csv(
        self,
        filename: str,
        rows: List[Dict[str, object]],
        fieldnames: List[str],
    ) -> str:
        output_dir = self._get_output_dir()
        output_path = output_dir / filename

        with output_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=fieldnames,
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(rows)

        return str(output_path)

    def export_dataset(self, dataset: List[Dict[str, object]]) -> str:
        path = self._write_csv(
            "opportunities_export.csv",
            dataset,
            OPPORTUNITY_DATASET_HEADERS,
        )
        self.ctx.paths["opportunities_export"] = path
        return path

    def export_top_dataset(self, dataset: List[Dict[str, object]]) -> str:
        path = self._write_csv(
            "top_opportunities_export.csv",
            dataset,
            OPPORTUNITY_DATASET_HEADERS,
        )
        self.ctx.paths["top_opportunities_export"] = path
        return path
