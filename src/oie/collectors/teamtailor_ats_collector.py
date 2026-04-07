from __future__ import annotations

import importlib
from typing import Any, Dict, List

from oie.collectors.base import BaseJobCollector


class TeamtailorATSCollector(BaseJobCollector):
    collector_name = "teamtailor"

    def _load_legacy_callable(self):
        function_candidates = [
            ("collectors.ats.teamtailor", "collect_jobs"),
            ("collectors.ats.teamtailor_collector", "collect_jobs"),
            ("collectors.teamtailor", "collect_jobs"),
        ]

        for module_name, function_name in function_candidates:
            try:
                module = importlib.import_module(module_name)
                fn = getattr(module, function_name, None)
                if callable(fn):
                    return ("function", fn)
            except Exception:
                continue

        class_candidates = [
            ("collectors.ats.teamtailor", "TeamtailorCollector"),
        ]

        for module_name, class_name in class_candidates:
            try:
                module = importlib.import_module(module_name)
                cls = getattr(module, class_name, None)
                if cls is not None:
                    instance = cls()
                    collect_method = getattr(instance, "collect", None)
                    if callable(collect_method):
                        return ("method", collect_method)
            except Exception:
                continue

        return None

    def _load_legacy_collector(self):
        legacy_target = self._load_legacy_callable()
        if legacy_target is None:
            return None

        target_type, target = legacy_target

        if target_type == "method":
            return lambda payload: target(payload)

        return target

    def _normalize_job(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "title": raw_job.get("title", ""),
            "company": raw_job.get("company", ""),
            "location": raw_job.get("location", ""),
            "job_url": raw_job.get("job_url", "") or raw_job.get("url", ""),
            "apply_url": raw_job.get("apply_url", ""),
            "description": raw_job.get("description", ""),
            "source": self.collector_name,
            "detected_at": raw_job.get("detected_at", ""),
            "url": raw_job.get("url", ""),
            "source_meta": raw_job.get("source_meta", {}) or {},
        }

    def collect(self) -> List[Dict[str, Any]]:
        legacy_collect_fn = self._load_legacy_collector()
        if legacy_collect_fn is None:
            return []

        queries = self.config.get("queries", []) or []
        run = self.config.get("run", {}) or {}
        source_config = self.config.get("source_config", {}) or {}
        payload = {
            "queries": queries,
            "run": run,
            "source_config": source_config,
            "collector_cfg": source_config,
        }

        try:
            raw_jobs = legacy_collect_fn(
                queries=queries,
                num_pages=run.get("num_pages", 3),
                sleep_s=run.get("sleep_s", 1.0),
                **source_config,
            ) or []
        except TypeError:
            try:
                raw_jobs = legacy_collect_fn(payload) or []
            except TypeError:
                raw_jobs = legacy_collect_fn() or []

        return [self._normalize_job(job) for job in raw_jobs]
