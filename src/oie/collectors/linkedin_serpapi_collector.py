from __future__ import annotations

from typing import Any, Dict, List

from oie.collectors.base import BaseJobCollector


class LinkedInSerpAPICollector(BaseJobCollector):

    collector_name = "linkedin_serpapi"

    def _load_legacy_collector(self):
        candidates = [
            ("collectors.discovery.linkedin_serpapi", "collect_jobs"),
            ("collectors.discovery.linkedin", "collect_jobs"),
            ("collectors.linkedin_serpapi", "collect_jobs"),
        ]

        for module_name, function_name in candidates:
            try:
                module = __import__(module_name, fromlist=[function_name])
                fn = getattr(module, function_name, None)
                if fn:
                    return fn
            except Exception:
                continue

        return None

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
        }

    def collect(self) -> List[Dict[str, Any]]:
        legacy_collect_fn = self._load_legacy_collector()
        if legacy_collect_fn is None:
            return []

        queries = self.config.get("queries", [])
        run = self.config.get("run", {})
        source_config = self.config.get("source_config", {})

        try:
            raw_jobs = legacy_collect_fn(
                queries=queries,
                num_pages=run.get("num_pages", 3),
                sleep_s=run.get("sleep_s", 1.0),
                gl=source_config.get("gl", "us"),
                hl=source_config.get("hl", "en"),
            ) or []
        except TypeError:
            raw_jobs = legacy_collect_fn() or []

        return [self._normalize_job(job) for job in raw_jobs]
