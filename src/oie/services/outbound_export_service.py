from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

from oie.orchestration.run_context import RunContext
from oie.services.opportunity_dataset_service import OpportunityDatasetService


TOP_OPPORTUNITIES_HEADERS = [
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
]

APOLLO_IMPORT_HEADERS = [
    "account_name",
    "website",
    "company_linkedin_url",
    "industry",
    "company_description",
    "first_name",
    "title",
    "email",
    "person_linkedin_url",
]


class OutboundExportService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.opportunity_dataset_service = OpportunityDatasetService(ctx)

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

    def _load_dataset(self, company_types: List[str] | None = None) -> List[Dict[str, object]]:
        rows = self.opportunity_dataset_service.build_dataset()

        if company_types:
            allowed = {value.strip().lower() for value in company_types}
            rows = [
                row for row in rows
                if str(row.get("company_type_ai") or "").strip().lower() in allowed
            ]

        rows.sort(
            key=lambda row: (
                float(row.get("opportunity_score") or 0),
                str(row.get("company_display") or ""),
            ),
            reverse=True,
        )
        return rows

    def export_top_opportunities(self, limit: int = 50) -> str:
        rows = self._load_dataset()[:limit]
        path = self._write_csv(
            "top_opportunities.csv",
            rows,
            TOP_OPPORTUNITIES_HEADERS,
        )
        self.ctx.paths["top_opportunities_csv"] = path
        return path

    def export_company_segment(self, segment_name: str, company_types: List[str]) -> str:
        rows = self._load_dataset(company_types=company_types)
        path = self._write_csv(
            f"{segment_name}.csv",
            rows,
            TOP_OPPORTUNITIES_HEADERS,
        )
        self.ctx.paths[f"{segment_name}_csv"] = path
        return path

    def export_apollo_import(self) -> str:
        dataset = self._load_dataset()
        rows: List[Dict[str, object]] = []

        for row in dataset:
            email = str(row.get("email") or "").strip()
            if not email:
                continue

            rows.append(
                {
                    "account_name": row.get("company_display", ""),
                    "website": row.get("resolved_domain", ""),
                    "company_linkedin_url": row.get("linkedin_company_url", ""),
                    "industry": row.get("industry", ""),
                    "company_description": row.get("company_description", ""),
                    "first_name": row.get("contact_name", ""),
                    "title": row.get("contact_title", ""),
                    "email": email,
                    "person_linkedin_url": row.get("linkedin_url", ""),
                }
            )

        path = self._write_csv(
            "apollo_import.csv",
            rows,
            APOLLO_IMPORT_HEADERS,
        )
        self.ctx.paths["apollo_import_csv"] = path
        return path

    def export_all(self) -> None:
        self.export_top_opportunities()
        self.export_company_segment("end_clients", ["end_client"])
        self.export_company_segment("vendors", ["staffing", "consulting"])
        self.export_company_segment("marketplaces", ["marketplace"])
        self.export_apollo_import()
