from __future__ import annotations

from typing import Any, Dict, List

from oie.collectors.base import BaseJobCollector


class StaticJobsCollector(BaseJobCollector):
    collector_name = "static_jobs"

    def collect(self) -> List[Dict[str, Any]]:
        jobs = self.config.get("jobs", []) or []
        return [
            {
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "job_url": job.get("job_url", ""),
                "apply_url": job.get("apply_url", ""),
                "description": job.get("description", ""),
                "source": self.collector_name,
                "detected_at": job.get("detected_at", ""),
            }
            for job in jobs
        ]
