from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List

from oie.orchestration.run_context import RunContext


class MasterDataSchemaError(RuntimeError):
    pass


class MasterDataService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.base_dir = Path(
            self.ctx.config.get("masters", {}).get("path", "data/masters")
        )
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _master_path(self, entity_name: str) -> Path:
        return self.base_dir / f"master_{entity_name}.csv"

    def _read_existing_rows(self, path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            return []

        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            return list(reader)

    def _get_existing_schema(self, path: Path) -> List[str]:
        if not path.exists():
            return []

        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            try:
                return next(reader)
            except StopIteration:
                return []

    def _validate_schema(self, path: Path, fieldnames: List[str]) -> None:
        existing_schema = self._get_existing_schema(path)
        if not existing_schema:
            return

        if existing_schema != fieldnames:
            raise MasterDataSchemaError(
                f"Schema mismatch for {path.name}. "
                f"existing={existing_schema} new={fieldnames}"
            )

    def _append_rows(
        self,
        path: Path,
        fieldnames: List[str],
        rows: List[Dict[str, Any]],
    ) -> int:
        if not rows:
            return 0

        file_exists = path.exists()
        with path.open("a", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerows(rows)

        return len(rows)

    def _with_run_metadata(self, rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        enriched: List[Dict[str, Any]] = []
        for row in rows:
            record = dict(row)
            record["run_id"] = self.ctx.run_id
            record["run_date"] = self.ctx.run_date
            enriched.append(record)
        return enriched

    def _normalize_rows_to_schema(
        self,
        rows: List[Dict[str, Any]],
        fieldnames: List[str],
    ) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for row in rows:
            normalized.append({field: row.get(field, "") for field in fieldnames})
        return normalized

    def append_entity_rows(
        self,
        entity_name: str,
        rows: List[Dict[str, Any]],
        fieldnames: List[str],
    ) -> int:
        path = self._master_path(entity_name)
        self._validate_schema(path, fieldnames)
        normalized_rows = self._normalize_rows_to_schema(rows, fieldnames)
        return self._append_rows(path, fieldnames, normalized_rows)

    def safe_append_entity_rows(
        self,
        entity_name: str,
        rows: List[Dict[str, Any]],
        fieldnames: List[str],
    ) -> int:
        try:
            count = self.append_entity_rows(entity_name, rows, fieldnames)
            self.ctx.metrics[f"master_{entity_name}_rows_written"] = count
            return count
        except MasterDataSchemaError as exc:
            self.ctx.metrics[f"master_{entity_name}_write_skipped_schema_error"] = True
            self.ctx.add_provider_event(
                provider="master_data",
                event_type="schema_error",
                message=str(exc),
                metadata={"entity_name": entity_name},
            )
            return 0

    def append_jobs(self, jobs: List[Dict[str, Any]]) -> int:
        rows = self._with_run_metadata(jobs)
        fieldnames = [
            "title",
            "company",
            "location",
            "job_url",
            "apply_url",
            "description",
            "source",
            "detected_at",
            "run_id",
            "run_date",
        ]
        return self.safe_append_entity_rows("jobs", rows, fieldnames)

    def append_companies(self, companies: List[Dict[str, Any]]) -> int:
        rows = self._with_run_metadata(companies)
        fieldnames = [
            "company_key",
            "company_display",
            "company_normalized",
            "company_root",
            "resolved_domain",
            "domain_source",
            "domain_confidence",
            "total_openings",
            "remote_jobs",
            "contractor_jobs",
            "opportunity_score",
            "run_id",
            "run_date",
        ]
        return self.safe_append_entity_rows("companies", rows, fieldnames)

    def append_leads(self, leads: List[Dict[str, Any]]) -> int:
        rows = self._with_run_metadata(leads)
        fieldnames = [
            "company_key",
            "contact_name",
            "contact_title",
            "email",
            "linkedin_url",
            "lead_source",
            "lead_confidence",
            "email_quality_score",
            "lead_capture_reason",
            "lead_relevance_score",
            "run_id",
            "run_date",
        ]
        return self.safe_append_entity_rows("leads", rows, fieldnames)

    def read_master_rows(self, entity_name: str) -> List[Dict[str, Any]]:
        return self._read_existing_rows(self._master_path(entity_name))
