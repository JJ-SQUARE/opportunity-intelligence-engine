# src/collectors/google_jobs/google_jobs_serpapi_collector.py
from __future__ import annotations

from typing import Any, Dict, List

from collectors.google_jobs.google_jobs_serpapi_client import fetch_google_jobs_serpapi
from collectors.registry import register


@register
class GoogleJobsSerpApiCollector:
    name = "google_jobs"
    source = "google_jobs"

    def collect(self, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
        run_cfg = cfg.get("run", {}) or {}
        num_pages = int(run_cfg.get("num_pages", 3))
        sleep_s = float(run_cfg.get("sleep_s", 1.0))
        timeout_s = float(run_cfg.get("timeout_s", 45.0))  # opcional

        c_cfg = cfg.get("collector_cfg", {}) or {}  # sources.google_jobs
        locations = c_cfg.get("locations", ["United States"])
        queries = cfg.get("queries", []) or []
        remote_fallback_location = c_cfg.get("remote_fallback_location", "United States")

        out: List[Dict[str, Any]] = []

        for q in queries:
            q_name = q.get("name", "query")
            q_text = q.get("q", "")

            for loc in locations:
                serp_location = loc
                serp_query = q_text

                # Si "Remote" viene como location, SerpApi google_jobs NO lo acepta:
                # usamos fallback_location y agregamos "remote" al query si hace falta.
                if isinstance(loc, str) and loc.strip().lower() == "remote":
                    serp_location = remote_fallback_location
                    if "remote" not in (serp_query or "").lower():
                        serp_query = f"{serp_query} remote"

                batch = fetch_google_jobs_serpapi(
                    query=serp_query,
                    location=serp_location,
                    num_pages=num_pages,
                    sleep_s=sleep_s,
                    timeout_s=timeout_s,
                )

                for j in batch:
                    j["source_meta"] = j.get("source_meta") or {}
                    j["source_meta"].update(
                        {
                            "query_name": q_name,
                            "query_text": q_text,
                            "search_location": loc,
                            "serp_location_used": serp_location,
                            "serp_query_used": serp_query,
                        }
                    )

                out.extend(batch)

        return out