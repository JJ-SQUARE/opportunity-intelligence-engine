from __future__ import annotations

import importlib
from typing import Any, Dict, List

from oie.collectors.base import BaseJobCollector


class GoogleJobsCollector(BaseJobCollector):
    collector_name = "google_jobs"

    def _load_legacy_callable(self):
        function_candidates = [
            ("collectors.google_jobs.google_jobs_collector", "collect_jobs"),
            ("collectors.google_jobs.collector", "collect_jobs"),
            ("collectors.google_jobs", "collect_jobs"),
            ("pipeline.google_jobs", "collect_jobs"),
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
            ("collectors.google_jobs.google_jobs_serpapi_collector", "GoogleJobsSerpApiCollector"),
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

    # Compatibilidad con tests antiguos que monkeypatchean este nombre.
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
            "remote_flag": raw_job.get("remote_flag", False),
            "contractor_flag": raw_job.get("contractor_flag", False),
            "url": raw_job.get("url", ""),
            "source_meta": raw_job.get("source_meta", {}) or {},
        }

    def collect(self) -> List[Dict[str, Any]]:
        legacy_collect_fn = self._load_legacy_collector()
        if legacy_collect_fn is None:
            return []

        queries = self.config.get("queries", []) or []
        run_config = self.config.get("run", {}) or {}
        source_config = self.config.get("source_config", {}) or {}

        locations = source_config.get("locations", []) or []
        location_mode = source_config.get("location_mode", "matrix")
        num_pages = run_config.get("num_pages", 3)
        sleep_s = run_config.get("sleep_s", 1.0)

        payload = {
            "queries": queries,
            "locations": locations,
            "location_mode": location_mode,
            "num_pages": num_pages,
            "sleep_s": sleep_s,
            "source_config": source_config,
            "collector_cfg": source_config,
            "run": run_config,
        }

        try:
            raw_jobs = legacy_collect_fn(payload) or []
        except TypeError:
            try:
                raw_jobs = legacy_collect_fn(
                    queries=queries,
                    locations=locations,
                    location_mode=location_mode,
                    num_pages=num_pages,
                    sleep_s=sleep_s,
                ) or []
            except TypeError:
                raw_jobs = legacy_collect_fn() or []

        return [self._normalize_job(job) for job in raw_jobs]
