from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class DomainReviewQueueService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def build_rows(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []

        for company in companies:
            if company.get("domain_validation_status") != "review":
                continue

            rows.append(
                {
                    "company_key": company.get("company_key"),
                    "company_display": company.get("company_display"),
                    "company_normalized": company.get("company_normalized"),
                    "domain_candidate": company.get("domain_candidate"),
                    "resolved_domain": company.get("resolved_domain"),
                    "domain_source": company.get("domain_source"),
                    "domain_confidence": company.get("domain_confidence"),
                    "domain_review_required": company.get("domain_review_required"),
                    "domain_ai_validated": company.get("domain_ai_validated"),
                    "domain_ai_decision": company.get("domain_ai_decision"),
                    "domain_ai_confidence": company.get("domain_ai_confidence"),
                    "domain_ai_reason": company.get("domain_ai_reason"),
                    "apply_url": company.get("apply_url"),
                    "url": company.get("url"),
                    "title": company.get("title"),
                    "snippet": company.get("snippet"),
                }
            )

        return rows

    def export_csv(self, companies: List[Dict[str, Any]]) -> str:
        rows = self.build_rows(companies)

        output_dir_value = self.ctx.paths.get("output_dir")
        if not output_dir_value:
            base_output = (
                (self.ctx.config or {}).get("outputs", {}).get("path")
                or "data/outputs"
            )
            run_id = self.ctx.run_id or "manual_run"
            output_dir_value = str(Path(base_output) / run_id)
            self.ctx.paths["output_dir"] = output_dir_value

        output_dir = Path(output_dir_value)
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "domain_review_queue.csv"

        fieldnames = [
            "company_key",
            "company_display",
            "company_normalized",
            "domain_candidate",
            "resolved_domain",
            "domain_source",
            "domain_confidence",
            "domain_review_required",
            "domain_ai_validated",
            "domain_ai_decision",
            "domain_ai_confidence",
            "domain_ai_reason",
            "apply_url",
            "url",
            "title",
            "snippet",
        ]

        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        self.ctx.metrics["domain_review_queue_count"] = len(rows)
        self.ctx.metrics["domain_review_queue_written"] = len(rows)
        self.ctx.paths["domain_review_queue_csv"] = str(out_path)

        return str(out_path)
