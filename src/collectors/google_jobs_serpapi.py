import os
import time
from typing import Any, Dict, List, Optional

import requests


SERPAPI_URL = "https://serpapi.com/search.json"


def fetch_google_jobs_serpapi(
    query: str,
    location: str = "United States",
    num_pages: int = 3,
    sleep_s: float = 1.0,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Collect job posts from Google Jobs via SerpApi.
    Normalizes key fields for downstream pipeline.

    Requires SERPAPI_KEY in env or passed as api_key.
    """
    api_key = api_key or os.getenv("SERPAPI_KEY")
    if not api_key:
        raise RuntimeError("Missing SERPAPI_KEY (set it in .env or environment variables).")

    jobs: List[Dict[str, Any]] = []
    next_page_token: Optional[str] = None

    for _ in range(max(1, num_pages)):
        params: Dict[str, Any] = {
            "engine": "google_jobs",
            "q": query,
            "location": location,
            "api_key": api_key,
        }
        if next_page_token:
            params["next_page_token"] = next_page_token

        r = requests.get(SERPAPI_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        for item in (data.get("jobs_results") or []):
            # Try to pick a best-effort URL for the posting
            url = None
            if item.get("related_links"):
                url = (item["related_links"][0] or {}).get("link")
            if not url and item.get("apply_options"):
                url = (item["apply_options"][0] or {}).get("link")

            jobs.append(
                {
                    "source": "google_jobs",
                    "job_title": item.get("title"),
                    "company": (item.get("company_name") or "").strip() or None,
                    "location": item.get("location"),
                    "date_posted": (item.get("detected_extensions") or {}).get("posted_at"),
                    "via": (item.get("detected_extensions") or {}).get("via"),
                    "url": url,
                    "description": item.get("description"),
                }
            )

        next_page_token = ((data.get("serpapi_pagination") or {}).get("next_page_token"))
        if not next_page_token:
            break

        time.sleep(max(0.0, sleep_s))

    return jobs