from __future__ import annotations
from typing import Any, Dict, List

from collectors.google_jobs_serpapi import fetch_google_jobs_serpapi
from collectors.registry import register

@register
class GoogleJobsSerpApiCollector:
    name = "google_jobs"
    source = "google_jobs"

    def collect(self, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
        run_cfg = cfg.get("run", {})
        num_pages = int(run_cfg.get("num_pages", 3))
        sleep_s = float(run_cfg.get("sleep_s", 1.0))

        c_cfg = cfg.get("collector_cfg", {})  # sources.google_jobs
        locations = c_cfg.get("locations", ["United States"])
        queries = cfg.get("queries", [])
        remote_fallback_location = c_cfg.get("remote_fallback_location", "United States")

        out: List[Dict[str, Any]] = []

        for q in queries:
            q_name = q.get("name", "query")
            q_text = q.get("q", "")

            for loc in locations:
                serp_location = loc
                serp_query = q_text

                if isinstance(loc, str) and loc.strip().lower() == "remote":
                    serp_location = remote_fallback_location
                    if "remote" not in (serp_query or "").lower():
                        serp_query = f"{serp_query} remote"

                batch = fetch_google_jobs_serpapi(
                    query=serp_query,
                    location=serp_location,
                    num_pages=num_pages,
                    sleep_s=sleep_s,
                )

                for j in batch:
                    j["source_meta"] = j.get("source_meta") or {}
                    j["source_meta"].update({
                        "query_name": q_name,
                        "query_text": q_text,
                        "search_location": loc,
                        "serp_location_used": serp_location,
                        "serp_query_used": serp_query,
                    })

                out.extend(batch)

        return out