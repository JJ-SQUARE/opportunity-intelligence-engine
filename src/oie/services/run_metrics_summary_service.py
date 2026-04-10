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
        data["counts_original"] = {
            "jobs_collected_raw": self._int_metric("jobs_collected_raw"),
            "jobs_after_dedupe": self._int_metric("jobs_after_dedupe"),
            "master_jobs_unique_to_append": self._int_metric("master_jobs_unique_to_append"),
            "companies_detected": self._int_metric("companies_detected"),
            "companies_after_identity_dedupe": self._int_metric("companies_after_identity_dedupe"),
            "leads_generated": self._int_metric("leads_generated"),
            "best_leads_selected": self._int_metric("best_leads_selected"),
            "master_leads_unique_to_append": self._int_metric("master_leads_unique_to_append"),
        }
        data["counts_effective"] = {
            "jobs": self._snapshot_int("jobs_count"),
            "companies": self._snapshot_int("companies_count"),
            "leads": self._snapshot_int("leads_count"),
        }
        return data
