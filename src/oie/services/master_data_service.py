from __future__ import annotations

import csv
import os
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

        existing_set = set(existing_schema)
        new_set = set(fieldnames)

        # Permitimos evolución aditiva del schema del master CSV:
        # si solo faltan columnas nuevas, migramos el archivo y preservamos datos.
        if existing_set.issubset(new_set):
            return

        raise MasterDataSchemaError(
            f"Schema mismatch for {path.name}. "
            f"existing={existing_schema} new={fieldnames}"
        )

    def _migrate_master_schema_if_needed(
        self,
        path: Path,
        fieldnames: List[str],
    ) -> int:
        existing_schema = self._get_existing_schema(path)
        if not existing_schema:
            return 0

        if existing_schema == fieldnames:
            return 0

        existing_set = set(existing_schema)
        new_set = set(fieldnames)

        # Solo migramos automáticamente cuando el cambio es aditivo.
        if not existing_set.issubset(new_set):
            raise MasterDataSchemaError(
                f"Schema mismatch for {path.name}. "
                f"existing={existing_schema} new={fieldnames}"
            )

        existing_rows = self._read_existing_rows(path)
        normalized_rows = self._normalize_rows_to_schema(existing_rows, fieldnames)

        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(normalized_rows)

        os.replace(tmp_path, path)
        return max(len(fieldnames) - len(existing_schema), 0)

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
        columns_added = self._migrate_master_schema_if_needed(path, fieldnames)

        if columns_added > 0:
            self.ctx.metrics[f"master_{entity_name}_schema_migrated"] = True
            self.ctx.metrics[f"master_{entity_name}_schema_columns_added"] = (
                int(self.ctx.metrics.get(f"master_{entity_name}_schema_columns_added", 0) or 0)
                + columns_added
            )
            self.ctx.metrics[f"master_{entity_name}_schema_migrations_count"] = (
                int(self.ctx.metrics.get(f"master_{entity_name}_schema_migrations_count", 0) or 0)
                + 1
            )

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
            self.ctx.metrics[f"master_{entity_name}_write_attempted"] = len(rows or [])
            self.ctx.metrics[f"master_{entity_name}_write_succeeded"] = True
            return count
        except MasterDataSchemaError as exc:
            self.ctx.metrics[f"master_{entity_name}_rows_written"] = 0
            self.ctx.metrics[f"master_{entity_name}_write_skipped_schema_error"] = True
            self.ctx.metrics[f"master_{entity_name}_write_succeeded"] = False
            self.ctx.metrics[f"master_{entity_name}_write_attempted"] = len(rows or [])
            self.ctx.metrics["master_schema_errors_count"] = int(
                self.ctx.metrics.get("master_schema_errors_count", 0) or 0
            ) + 1
            self.ctx.add_provider_event(
                provider="master_data",
                event_type="schema_error",
                message=str(exc),
                metadata={"entity_name": entity_name},
            )
            return 0
        except Exception as exc:
            self.ctx.metrics[f"master_{entity_name}_rows_written"] = 0
            self.ctx.metrics[f"master_{entity_name}_write_failed_error"] = True
            self.ctx.metrics[f"master_{entity_name}_write_succeeded"] = False
            self.ctx.metrics[f"master_{entity_name}_write_attempted"] = len(rows or [])
            self.ctx.metrics[f"master_{entity_name}_write_errors_count"] = int(
                self.ctx.metrics.get(f"master_{entity_name}_write_errors_count", 0) or 0
            ) + 1
            self.ctx.add_provider_event(
                provider="master_data",
                event_type="write_error",
                message=str(exc),
                metadata={"entity_name": entity_name},
            )
            return 0

    def append_jobs(self, jobs: List[Dict[str, Any]]) -> int:
        rows = self._with_run_metadata(jobs)
        fieldnames = [
            "company_key",
            "title",
            "company",
            "location",
            "job_url",
            "apply_url",
            "description",
            "source",
            "detected_at",
            "is_remote",
            "is_contractor",
            "is_full_time",
            "nearshore_friendly",
            "us_only",
            "remote_flag",
            "contractor_flag",
            "many_openings_signal",
            "offshore_mentioned",
            "urgency_hits",
            "job_fingerprint",
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
            "domain_candidate",
            "domain_validation_status",
            "domain_review_required",
            "domain_ai_validated",
            "domain_ai_decision",
            "domain_ai_confidence",
            "domain_ai_reason",
            "ai_company_identity_confidence",
            "ai_company_identity_source",
            "ai_company_identity_reason",
            "company_identity_ai_valid",
            "company_identity_ai_contaminated",
            "company_identity_ai_ambiguous",
            "company_type_ai",
            "classification_confidence_ai",
            "classification_provider",
            "industry",
            "employee_range",
            "company_size",
            "linkedin_company_url",
            "company_description",
            "enriched_at",
            "enrichment_source",
            "enrichment_ai_match",
            "enrichment_ai_confidence",
            "enrichment_ai_decision",
            "enrichment_ai_reason",
            "enrichment_ai_provider",
            "enrichment_ai_model",
            "enrichment_ai_mode",
            "total_openings",
            "remote_jobs",
            "contractor_jobs",
            "remote_ratio",
            "contractor_ratio",
            "remote_friendly",
            "contractor_signal",
            "multi_source_signal",
            "opportunity_score",
            "opportunity_label",
            "score_openings",
            "score_remote",
            "score_contractor",
            "score_multi_source",
            "score_company_type",
            "score_icp_fit",
            "score_pain_urgency",
            "score_region_fit",
            "score_company_scale",
            "score_role_seniority_mix",
            "score_penalty_competitor",
            "score_penalty_negative_signals",
            "primary_service_fit",
            "buyer_persona_fit",
            "opportunity_score_reason",
            "scoring_provider",
            "scoring_model",
            "scoring_mode",
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
            "lead_fingerprint",
            "email_quality_score",
            "lead_capture_reason",
            "lead_relevance_score",
            "lead_priority_label",
            "lead_decision_maker_score",
            "lead_icp_fit_score",
            "lead_contact_completeness_score",
            "lead_penalty_negative_title",
            "lead_score_reason",
            "lead_scoring_provider",
            "lead_scoring_model",
            "lead_scoring_mode",
            "lead_score_title",
            "lead_score_source",
            "lead_score_email",
            "lead_score_linkedin",
            "lead_score_email_quality",
            "lead_score_confidence",
            "lead_score_completeness_penalty",
            "lead_score_company_penalty",
            "target_persona",
            "suggested_titles",
            "search_reason",
            "pain_alignment",
            "priority",
            "recommended_channel",
            "lead_role_type",
            "why_selected",
            "outreach_angle",
            "expected_relevance",
            "risk_or_uncertainty",
            "run_id",
            "run_date",
        ]
        return self.safe_append_entity_rows("leads", rows, fieldnames)

    def read_master_rows(self, entity_name: str) -> List[Dict[str, Any]]:
        return self._read_existing_rows(self._master_path(entity_name))
