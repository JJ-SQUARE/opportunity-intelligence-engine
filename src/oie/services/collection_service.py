from __future__ import annotations

from typing import Any, Dict, List

from oie.collectors.ashby_ats_collector import AshbyATSCollector
from oie.collectors.breezy_ats_collector import BreezyATSCollector
from oie.collectors.career_pages_serpapi_collector import CareerPagesSerpAPICollector
from oie.collectors.google_jobs_collector import GoogleJobsCollector
from oie.collectors.greenhouse_ats_collector import GreenhouseATSCollector
from oie.collectors.indeed_serpapi_collector import IndeedSerpAPICollector
from oie.collectors.lever_ats_collector import LeverATSCollector
from oie.collectors.linkedin_serpapi_collector import LinkedInSerpAPICollector
from oie.collectors.recruitee_ats_collector import RecruiteeATSCollector
from oie.collectors.smartrecruiters_ats_collector import SmartRecruitersATSCollector
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
        if (discovery.get("indeed_serpapi", {}) or {}).get("enabled", False):
            enabled.append("indeed_serpapi")
        if (discovery.get("career_pages_serpapi", {}) or {}).get("enabled", False):
            enabled.append("career_pages_serpapi")

        ats = sources.get("ats", {}) or {}
        if (ats.get("greenhouse", {}) or {}).get("enabled", False):
            enabled.append("greenhouse")
        if (ats.get("lever", {}) or {}).get("enabled", False):
            enabled.append("lever")
        if (ats.get("workable", {}) or {}).get("enabled", False):
            enabled.append("workable")
        if (ats.get("teamtailor", {}) or {}).get("enabled", False):
            enabled.append("teamtailor")
        if (ats.get("breezy", {}) or {}).get("enabled", False):
            enabled.append("breezy")
        if (ats.get("smartrecruiters", {}) or {}).get("enabled", False):
            enabled.append("smartrecruiters")
        if (ats.get("ashby", {}) or {}).get("enabled", False):
            enabled.append("ashby")
        if (ats.get("recruitee", {}) or {}).get("enabled", False):
            enabled.append("recruitee")

        static_jobs = (self.ctx.config.get("collectors", {}) or {}).get("static_jobs", {}) or {}
        if static_jobs.get("jobs"):
            enabled.append("static_jobs")

        return enabled

    def _normalize_queries(self, queries: List[Any]) -> List[Dict[str, str]]:
        normalized: List[Dict[str, str]] = []

        for idx, q in enumerate(queries or [], start=1):
            if isinstance(q, dict):
                q_name = str(q.get("name") or f"query_{idx}")
                q_text = str(q.get("q") or q.get("query") or "").strip()
                if q_text:
                    normalized.append({"name": q_name, "q": q_text})
                continue

            q_text = str(q).strip()
            if q_text:
                normalized.append({"name": f"query_{idx}", "q": q_text})

        return normalized

    def _build_collectors(self) -> None:
        if self._collectors_built:
            return

        sources = self.ctx.config.get("sources", {}) or {}
        run_config = self.ctx.config.get("run", {}) or {}
        queries = self._normalize_queries(self.ctx.config.get("queries", []) or [])

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
            "source_config": (sources.get("discovery", {}).get("linkedin_serpapi", {})),
        }

        indeed_config = {
            "queries": queries,
            "run": run_config,
            "source_config": (sources.get("discovery", {}).get("indeed_serpapi", {})),
        }

        career_pages_config = {
            "queries": queries,
            "run": run_config,
            "source_config": (sources.get("discovery", {}).get("career_pages_serpapi", {})),
        }

        greenhouse_config = {
            "queries": queries,
            "run": run_config,
            "source_config": (sources.get("ats", {}).get("greenhouse", {})),
        }

        lever_config = {
            "queries": queries,
            "run": run_config,
            "source_config": (sources.get("ats", {}).get("lever", {})),
        }

        workable_config = {
            "queries": queries,
            "run": run_config,
            "source_config": (sources.get("ats", {}).get("workable", {})),
        }

        teamtailor_config = {
            "queries": queries,
            "run": run_config,
            "source_config": (sources.get("ats", {}).get("teamtailor", {})),
        }

        breezy_config = {
            "queries": queries,
            "run": run_config,
            "source_config": (sources.get("ats", {}).get("breezy", {})),
        }

        smartrecruiters_config = {
            "queries": queries,
            "run": run_config,
            "source_config": (sources.get("ats", {}).get("smartrecruiters", {})),
        }

        ashby_config = {
            "queries": queries,
            "run": run_config,
            "source_config": (sources.get("ats", {}).get("ashby", {})),
        }

        recruitee_config = {
            "queries": queries,
            "run": run_config,
            "source_config": (sources.get("ats", {}).get("recruitee", {})),
        }

        self.collector_runner.register_collectors(
            [
                StaticJobsCollector(config=static_jobs_config),
                GoogleJobsCollector(config=google_jobs_config),
                LinkedInSerpAPICollector(config=linkedin_config),
                IndeedSerpAPICollector(config=indeed_config),
                CareerPagesSerpAPICollector(config=career_pages_config),
                GreenhouseATSCollector(config=greenhouse_config),
                LeverATSCollector(config=lever_config),
                WorkableATSCollector(config=workable_config),
                TeamtailorATSCollector(config=teamtailor_config),
                BreezyATSCollector(config=breezy_config),
                SmartRecruitersATSCollector(config=smartrecruiters_config),
                AshbyATSCollector(config=ashby_config),
                RecruiteeATSCollector(config=recruitee_config),
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
