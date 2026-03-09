from __future__ import annotations

from typing import Any, Dict, List

from oie.collectors.google_jobs_collector import GoogleJobsCollector
from oie.collectors.greenhouse_ats_collector import GreenhouseATSCollector
from oie.collectors.lever_ats_collector import LeverATSCollector
from oie.collectors.linkedin_serpapi_collector import LinkedInSerpAPICollector
from oie.collectors.static_jobs_collector import StaticJobsCollector
from oie.collectors.teamtailor_ats_collector import TeamtailorATSCollector
from oie.collectors.workable_ats_collector import WorkableATSCollector
from oie.orchestration.run_context import RunContext
from oie.services.collector_runner_service import CollectorRunnerService


class CollectionService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.collector_runner = CollectorRunnerService(ctx)
        self._collectors_built = False

    def _extract_enabled_collectors_from_yaml(self) -> List[str]:
        enabled: List[str] = []
        sources = self.ctx.config.get("sources", {}) or {}

        if (sources.get("google_jobs", {}) or {}).get("enabled", False):
            enabled.append("google_jobs")

        discovery = sources.get("discovery", {}) or {}
        if (discovery.get("linkedin_serpapi", {}) or {}).get("enabled", False):
            enabled.append("linkedin_serpapi")

        ats = sources.get("ats", {}) or {}
        if (ats.get("greenhouse", {}) or {}).get("enabled", False):
            enabled.append("greenhouse")
        if (ats.get("lever", {}) or {}).get("enabled", False):
            enabled.append("lever")
        if (ats.get("workable", {}) or {}).get("enabled", False):
            enabled.append("workable")
        if (ats.get("teamtailor", {}) or {}).get("enabled", False):
            enabled.append("teamtailor")

        return enabled

    def _build_collectors(self) -> None:
        if self._collectors_built:
            return

        sources = self.ctx.config.get("sources", {}) or {}
        run_config = self.ctx.config.get("run", {}) or {}
        queries = self.ctx.config.get("queries", []) or []

        static_jobs_config = (
            (self.ctx.config.get("collectors", {}) or {}).get("static_jobs", {}) or {}
        )

        google_jobs_config = {
            "queries": queries,
            "run": run_config,
            "source_config": sources.get("google_jobs", {}) or {},
        }

        linkedin_config = {
            "queries": queries,
            "run": run_config,
            "source_config": (
                sources.get("discovery", {}).get("linkedin_serpapi", {})
            ),
        }

        greenhouse_config = {
            "queries": queries,
            "run": run_config,
            "source_config": (
                sources.get("ats", {}).get("greenhouse", {})
            ),
        }

        lever_config = {
            "queries": queries,
            "run": run_config,
            "source_config": (
                sources.get("ats", {}).get("lever", {})
            ),
        }

        workable_config = {
            "queries": queries,
            "run": run_config,
            "source_config": (
                sources.get("ats", {}).get("workable", {})
            ),
        }

        teamtailor_config = {
            "queries": queries,
            "run": run_config,
            "source_config": (
                sources.get("ats", {}).get("teamtailor", {})
            ),
        }

        self.collector_runner.register_collectors(
            [
                StaticJobsCollector(config=static_jobs_config),
                GoogleJobsCollector(config=google_jobs_config),
                LinkedInSerpAPICollector(config=linkedin_config),
                GreenhouseATSCollector(config=greenhouse_config),
                LeverATSCollector(config=lever_config),
                WorkableATSCollector(config=workable_config),
                TeamtailorATSCollector(config=teamtailor_config),
            ]
        )

        self._collectors_built = True

    def collect(self) -> List[Dict[str, Any]]:
        self._build_collectors()

        enabled_names = self._extract_enabled_collectors_from_yaml()
        jobs = self.collector_runner.run_enabled_collectors(enabled_names=enabled_names)

        self.ctx.metrics["jobs_collected_raw"] = len(jobs)
        self.ctx.metrics["collect_completed"] = True

        return jobs
