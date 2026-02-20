# src/collectors/google_jobs/google_jobs_serpapi_client.py
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import requests

SERPAPI_URL = "https://serpapi.com/search.json"


def _extract_next_page_token(data: Dict[str, Any]) -> Optional[str]:
    """
    SerpApi can return pagination tokens in slightly different places depending on engine/version.
    We try a few known shapes.
    """
    for key in ("serpapi_pagination", "pagination", "search_information"):
        block = data.get(key)
        if isinstance(block, dict):
            tok = block.get("next_page_token")
            if tok:
                return str(tok)

    # sometimes nested differently
    block = data.get("serpapi_pagination") or {}
    if isinstance(block, dict):
        tok = block.get("next_page_token")
        if tok:
            return str(tok)

    return None


def _request_serpapi(params: Dict[str, Any], timeout_s: float, max_retries: int) -> Dict[str, Any]:
    """
    Retries for transient errors (429, 5xx, timeouts).
    """
    last_err: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            r = requests.get(SERPAPI_URL, params=params, timeout=timeout_s)

            # Retry on rate limits / transient server issues
            if r.status_code in (429, 500, 502, 503, 504):
                # exponential backoff with a small base
                sleep_s = min(20.0, 1.0 * (2 ** attempt) + 0.25)
                print(
                    f"[serpapi][WARN] status={r.status_code} retry_in={sleep_s:.2f}s "
                    f"engine={params.get('engine')}"
                )
                time.sleep(sleep_s)
                continue

            r.raise_for_status()
            return r.json()

        except Exception as e:
            last_err = e
            sleep_s = min(20.0, 1.0 * (2 ** attempt) + 0.25)
            print(
                f"[serpapi][WARN] request_error={type(e).__name__} retry_in={sleep_s:.2f}s "
                f"engine={params.get('engine')}"
            )
            time.sleep(sleep_s)

    # out of retries
    raise last_err or RuntimeError("SerpApi request failed")


def fetch_google_jobs_serpapi(
    query: str,
    location: str,
    num_pages: int = 3,
    sleep_s: float = 1.0,
    api_key_env: str = "SERPAPI_KEY",
    timeout_s: float = 45.0,
    max_retries: int = 3,
) -> List[Dict[str, Any]]:
    """
    Fetch jobs from SerpApi Google Jobs engine.

    IMPORTANT (Google Jobs pagination):
    - 'start' is discontinued; must use 'next_page_token' from response.
    """
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing env var: {api_key_env}")

    all_jobs: List[Dict[str, Any]] = []
    next_page_token: Optional[str] = None

    for page in range(max(1, int(num_pages))):
        params: Dict[str, Any] = {
            "engine": "google_jobs",
            "q": query,
            "location": location,
            "api_key": api_key,
        }

        # only include token when we actually have one
        if next_page_token:
            params["next_page_token"] = next_page_token

        data = _request_serpapi(params=params, timeout_s=timeout_s, max_retries=max_retries)

        jobs = data.get("jobs_results") or []
        if not isinstance(jobs, list):
            jobs = []

        for j in jobs:
            # SerpApi google_jobs fields vary; keep robust
            title = (j.get("title") or "").strip()
            company = (j.get("company_name") or j.get("company") or "").strip()

            # best-effort URL: prefer share_link; fallback to first apply option link
            share_link = j.get("share_link")
            apply_options = j.get("apply_options") or []
            apply_url = None
            if isinstance(apply_options, list) and apply_options:
                first = apply_options[0] or {}
                if isinstance(first, dict):
                    apply_url = first.get("link")

            job_url = share_link or apply_url  # canonical listing link if available

            location_name = j.get("location") or None
            description = j.get("description") or None

            out = {
                "title": title or None,
                "company": company or None,
                "location": location_name,
                "description": description,
                "job_url": job_url,
                "apply_url": apply_url,
                "source_id": j.get("job_id"),
                "source_meta": {
                    "engine": "google_jobs",
                    "serpapi_location": location,
                    "serpapi_query": query,
                },
                "raw": j,
            }
            all_jobs.append(out)

        # pagination token for next loop
        next_page_token = _extract_next_page_token(data)

        # If no token, stop early (no more pages)
        if not next_page_token:
            break

        time.sleep(max(0.0, float(sleep_s)))

    return all_jobs