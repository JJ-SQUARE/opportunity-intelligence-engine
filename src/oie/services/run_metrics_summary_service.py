from __future__ import annotations

from typing import Any, Dict

from oie.models.run_metrics import RunMetrics
from oie.orchestration.run_context import RunContext


class RunMetricsSummaryService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def _int_metric(self, key: str) -> int:
        value = self.ctx.metrics.get(key, 0)
        try:
            return int(value)
        except Exception:
            return 0

    def _snapshot_int(self, key: str) -> int:
        snapshot = self.ctx.provider_state.get("run_metrics_summary_counts", {}) or {}
        value = snapshot.get(key, 0)
        try:
            return int(value)
        except Exception:
            return 0

    def _int_metric_or_snapshot(self, key: str, snapshot_key: str) -> int:
        snapshot = self.ctx.provider_state.get("run_metrics_summary_counts", {}) or {}
        if snapshot_key in snapshot:
            return self._snapshot_int(snapshot_key)

        if key in self.ctx.metrics:
            return self._int_metric(key)

        return 0

    def _bool_metric(self, key: str) -> bool:
        value = self.ctx.metrics.get(key, False)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes"}

    def _float_metric(self, key: str) -> float:
        value = self.ctx.metrics.get(key, 0.0)
        try:
            return float(value or 0.0)
        except Exception:
            return 0.0

    def _provider_cost_usd(self, provider: str) -> float:
        prefix = f"{provider}_"
        total = self._float_metric(f"{provider}_cost_usd")
        for metric_key, metric_value in self.ctx.metrics.items():
            if not metric_key.startswith(prefix) or not metric_key.endswith("_cost_usd"):
                continue
            if metric_key == f"{provider}_cost_usd":
                continue
            try:
                total += float(metric_value or 0.0)
            except Exception:
                continue
        return round(total, 6)

    def _build_provider_errors(self) -> Dict[str, Dict[str, int]]:
        grouped: Dict[str, Dict[str, int]] = {}

        for metric_key, metric_value in self.ctx.metrics.items():
            if "_errors_" not in metric_key:
                continue

            try:
                value = int(metric_value or 0)
            except Exception:
                value = 0

            if value <= 0:
                continue

            provider, error_type = metric_key.split("_errors_", 1)
            if "_" in provider:
                provider = provider.split("_", 1)[0]

            grouped.setdefault(provider, {})
            grouped[provider][error_type] = grouped[provider].get(error_type, 0) + value

        return grouped

    def _build_provider_blocks(self) -> Dict[str, Dict[str, int]]:
        grouped: Dict[str, Dict[str, int]] = {}

        for metric_key, metric_value in self.ctx.metrics.items():
            if metric_key.endswith("_blocked_budget"):
                category = "blocked_budget"
                prefix = metric_key[: -len("_blocked_budget")]
            elif metric_key.endswith("_blocked_provider"):
                category = "blocked_provider"
                prefix = metric_key[: -len("_blocked_provider")]
            else:
                continue

            try:
                value = int(metric_value or 0)
            except Exception:
                value = 0

            if value <= 0:
                continue

            provider = prefix.split("_", 1)[0]
            grouped.setdefault(provider, {})
            grouped[provider][category] = grouped[provider].get(category, 0) + value

        return grouped

    def build_summary(self) -> Dict[str, Any]:
        summary = RunMetrics(
            jobs_collected=self._int_metric_or_snapshot("jobs_collected_raw", "jobs_count"),
            jobs_after_dedupe=self._int_metric_or_snapshot("jobs_after_dedupe", "jobs_count"),
            jobs_deduplicated=self._int_metric("jobs_deduplicated"),
            jobs_duplicates_detected=self._int_metric("master_jobs_duplicates_detected"),
            jobs_unique_to_append=self._int_metric_or_snapshot("master_jobs_unique_to_append", "jobs_count"),
            companies_detected=self._int_metric_or_snapshot("companies_detected", "companies_count"),
            companies_after_identity_dedupe=self._int_metric_or_snapshot("companies_after_identity_dedupe", "companies_count"),
            companies_with_domain=self._int_metric("companies_with_domain"),
            companies_enriched=self._int_metric("companies_enriched"),
            companies_classified=self._int_metric("companies_classified"),
            companies_scored=self._int_metric("companies_scored"),
            leads_generated=self._int_metric_or_snapshot("leads_generated", "leads_count"),
            leads_ranked=self._int_metric_or_snapshot("leads_ranked", "leads_count"),
            best_leads_selected=self._int_metric_or_snapshot("best_leads_selected", "leads_count"),
            leads_duplicates_detected=self._int_metric("master_leads_duplicates_detected"),
            leads_unique_to_append=self._int_metric_or_snapshot("master_leads_unique_to_append", "leads_count"),
            domain_resolution_accepted=self._int_metric("domain_resolution_accepted"),
            domain_resolution_review=self._int_metric("domain_resolution_review"),
            domain_resolution_rejected=self._int_metric("domain_resolution_rejected"),
            domain_review_queue_count=self._int_metric("domain_review_queue_count"),
            provider_events_count=len(self.ctx.provider_events),
            run_readiness_ready=self._bool_metric("run_readiness_ready"),
            run_readiness_warnings=self._int_metric("run_readiness_warnings"),
            provider_errors=self._build_provider_errors(),
            provider_blocks=self._build_provider_blocks(),
        )

        data = summary.to_dict()
        data["master_data"] = {
            "schema_errors_count": self._int_metric("master_schema_errors_count"),
            "jobs_rows_written": self._int_metric("master_jobs_rows_written"),
            "companies_rows_written": self._int_metric("master_companies_rows_written"),
            "leads_rows_written": self._int_metric("master_leads_rows_written"),
            "jobs_write_attempted": self._int_metric("master_jobs_write_attempted"),
            "companies_write_attempted": self._int_metric("master_companies_write_attempted"),
            "leads_write_attempted": self._int_metric("master_leads_write_attempted"),
            "jobs_write_succeeded": self._bool_metric("master_jobs_write_succeeded"),
            "companies_write_succeeded": self._bool_metric("master_companies_write_succeeded"),
            "leads_write_succeeded": self._bool_metric("master_leads_write_succeeded"),
            "jobs_write_errors_count": self._int_metric("master_jobs_write_errors_count"),
            "companies_write_errors_count": self._int_metric("master_companies_write_errors_count"),
            "leads_write_errors_count": self._int_metric("master_leads_write_errors_count"),
        }
        data["persistence_data"] = {
            "errors_count": self._int_metric("persistence_errors_count"),
            "schema_errors_count": self._int_metric("persistence_schema_errors_count"),
            "sqlite_operational_errors_count": self._int_metric("persistence_sqlite_operational_errors_count"),
            "database_initialized": self._bool_metric("persistence_database_initialized"),
            "initialize_attempted": self._bool_metric("persistence_initialize_attempted"),
            "initialize_succeeded": self._bool_metric("persistence_initialize_succeeded"),
            "run_attempted": self._bool_metric("persistence_run_attempted"),
            "run_succeeded": self._bool_metric("persistence_run_succeeded"),
            "metrics_attempted": self._bool_metric("persistence_metrics_attempted"),
            "metrics_succeeded": self._bool_metric("persistence_metrics_succeeded"),
            "provider_events_attempted": self._bool_metric("persistence_provider_events_attempted"),
            "provider_events_succeeded": self._bool_metric("persistence_provider_events_succeeded"),
            "provider_operation_metrics_attempted": self._bool_metric("persistence_provider_operation_metrics_attempted"),
            "provider_operation_metrics_succeeded": self._bool_metric("persistence_provider_operation_metrics_succeeded"),
            "companies_attempted": self._bool_metric("persistence_companies_attempted"),
            "companies_succeeded": self._bool_metric("persistence_companies_succeeded"),
            "jobs_attempted": self._bool_metric("persistence_jobs_attempted"),
            "jobs_succeeded": self._bool_metric("persistence_jobs_succeeded"),
            "leads_attempted": self._bool_metric("persistence_leads_attempted"),
            "leads_succeeded": self._bool_metric("persistence_leads_succeeded"),
        }
        data["counts_original"] = {
            "jobs_collected_raw": self._int_metric("jobs_collected_raw"),
            "jobs_after_dedupe": self._int_metric("jobs_after_dedupe"),
            "jobs_duplicates_detected_master": self._int_metric("master_jobs_duplicates_detected"),
            "jobs_unique_to_append_master": self._int_metric("master_jobs_unique_to_append"),
            "companies_detected": self._int_metric("companies_detected"),
            "companies_after_identity_dedupe": self._int_metric("companies_after_identity_dedupe"),
            "leads_generated": self._int_metric("leads_generated"),
            "best_leads_selected": self._int_metric("best_leads_selected"),
            "leads_duplicates_detected_master": self._int_metric("master_leads_duplicates_detected"),
            "leads_unique_to_append_master": self._int_metric("master_leads_unique_to_append"),
        }
        jobs_effective = self._int_metric_or_snapshot("master_jobs_unique_to_append", "jobs_count")
        companies_effective = self._int_metric_or_snapshot("companies_after_identity_dedupe", "companies_count")
        leads_effective = self._int_metric_or_snapshot("master_leads_unique_to_append", "leads_count")

        data["counts_effective"] = {
            "jobs": jobs_effective,
            "companies": companies_effective,
            "leads": leads_effective,
            "jobs_snapshot": self._snapshot_int("jobs_count"),
            "companies_snapshot": self._snapshot_int("companies_count"),
            "leads_snapshot": self._snapshot_int("leads_count"),
        }
        data["count_deltas"] = {
            "jobs_removed_by_master_dedup": max(
                data["counts_original"]["jobs_after_dedupe"] - data["counts_effective"]["jobs"],
                0,
            ),
            "companies_removed_after_identity": max(
                data["counts_original"]["companies_detected"] - data["counts_effective"]["companies"],
                0,
            ),
            "leads_removed_by_master_dedup": max(
                data["counts_original"]["best_leads_selected"] - data["counts_effective"]["leads"],
                0,
            ),
        }
        data["counts_quality"] = {
            "jobs_effective_uses_snapshot": data["counts_effective"]["jobs"] == data["counts_effective"]["jobs_snapshot"],
            "companies_effective_uses_snapshot": data["counts_effective"]["companies"] == data["counts_effective"]["companies_snapshot"],
            "leads_effective_uses_snapshot": data["counts_effective"]["leads"] == data["counts_effective"]["leads_snapshot"],
            "jobs_effective_lt_original": data["counts_effective"]["jobs"] <= data["counts_original"]["jobs_after_dedupe"],
            "companies_effective_lte_detected": data["counts_effective"]["companies"] <= data["counts_original"]["companies_detected"],
            "leads_effective_lte_selected": data["counts_effective"]["leads"] <= data["counts_original"]["best_leads_selected"],
            "master_jobs_rows_match_effective": data["master_data"]["jobs_rows_written"] == data["counts_effective"]["jobs"],
            "master_companies_rows_match_effective": (
                data["master_data"]["companies_rows_written"] == data["counts_effective"]["companies"]
                if data["master_data"]["companies_rows_written"] > 0
                else True
            ),
            "master_leads_rows_match_effective": data["master_data"]["leads_rows_written"] == data["counts_effective"]["leads"],
            "effective_counts_are_not_higher_than_snapshots": (
                data["counts_effective"]["jobs"] <= max(data["counts_effective"]["jobs_snapshot"], 0)
                and data["counts_effective"]["companies"] <= max(data["counts_effective"]["companies_snapshot"], 0)
                and data["counts_effective"]["leads"] <= max(data["counts_effective"]["leads_snapshot"], 0)
            ),
        }
        data["run_progress_metrics"] = {
            "jobs_collected_raw": data["counts_original"]["jobs_collected_raw"],
            "jobs_effective": data["counts_effective"]["jobs"],
            "jobs_analyzed_by_ai": self._int_metric("jobs_analyzed_by_ai") or self._int_metric("job_intelligence_jobs_analyzed"),
            "jobs_contaminated": self._int_metric("jobs_contaminated"),
            "companies_detected_raw": data["counts_original"]["companies_detected"],
            "companies_effective": data["counts_effective"]["companies"],
            "companies_discarded_by_ai": self._int_metric("companies_discarded_by_ai"),
            "companies_actionable": self._int_metric("companies_commercial_candidates"),
            "companies_enriched": data["companies_enriched"],
            "leads_found_raw": data["counts_original"]["leads_generated"],
            "leads_effective": data["counts_effective"]["leads"],
            "leads_useful": self._int_metric("leads_useful"),
            "leads_selected": data["best_leads_selected"],
            "ai_cost_usd": self._provider_cost_usd("openai"),
            "apollo_hunter_cost_usd": round(
                self._provider_cost_usd("apollo") + self._provider_cost_usd("hunter"),
                6,
            ),
            "commercial_ready": self._bool_metric("run_readiness_commercial_ready"),
        }

        self.ctx.provider_state["run_metrics_summary_counts_original"] = dict(data["counts_original"])
        self.ctx.provider_state["run_metrics_summary_counts_effective"] = dict(data["counts_effective"])
        self.ctx.provider_state["run_metrics_summary_counts"] = {
            "jobs_count": data["counts_effective"]["jobs"],
            "companies_count": data["counts_effective"]["companies"],
            "leads_count": data["counts_effective"]["leads"],
        }

        return data
