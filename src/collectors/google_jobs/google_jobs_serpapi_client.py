# src/collectors/google_jobs/google_jobs_serpapi_client.py
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import requests

SERPAPI_URL = "https://serpapi.com/search.json"


def fetch_google_jobs_serpapi(
    query: str,
    location: str,
    num_pages: int = 3,
    sleep_s: float = 1.0,
    api_key_env: str = "SERPAPI_KEY",
) -> List[Dict[str, Any]]:
    """
    Fetch jobs from SerpApi Google Jobs.

    IMPORTANT:
    - This function returns a list of dicts in your STANDARD Job schema (or close to it),
      and the collector will add source_meta, collector, etc.
    - If you already have a working implementation elsewhere, move it here.
    """
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing env var: {api_key_env}")

    all_jobs: List[Dict[str, Any]] = []

    for page in range(num_pages):
        params: Dict[str, Any] = {
            "engine": "google_jobs",
            "q": query,
            "location": location,
            "api_key": api_key,
            "start": page * 10,  # serpapi uses offset for pagination commonly
        }

        r = requests.get(SERPAPI_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        jobs = data.get("jobs_results") or []
        for j in jobs:
            # Minimal normalization to your base schema fields
            title = j.get("title") or ""
            company = (j.get("company_name") or j.get("company") or "").strip()
            job_url = j.get("job_id")  # not always a URL
            apply_options = j.get("apply_options") or []
            apply_url = None
            if apply_options and isinstance(apply_options, list):
                apply_url = apply_options[0].get("link")

            location_name = j.get("location") or None
            description = j.get("description") or None

            # Standard-ish output (ajústalo a tu JobPosting schema si ya lo tienes)
            out = {
                "title": title,
                "company": company,
                "location": location_name,
                "description": description,
                "job_url": apply_url or None,
                "apply_url": apply_url or None,
                "source": "google_jobs",
                "collector": "google_jobs_serpapi",
                "source_id": j.get("job_id"),
                "source_meta": {
                    "serpapi_raw": j,
                },
            }
            all_jobs.append(out)

        time.sleep(max(0.0, sleep_s))

    return all_jobs