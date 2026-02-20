from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import requests

SERPAPI_URL = "https://serpapi.com/search.json"


def _raise_for_status_with_body(r: requests.Response) -> None:
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        body = None
        try:
            body = r.text
        except Exception:
            body = None
        msg = f"{e}"
        if body:
            msg += f" | body={body}"
        raise requests.HTTPError(msg, response=r) from None


def fetch_google_search_serpapi(
    q: str,
    gl: str = "us",
    hl: str = "en",
    num_pages: int = 1,
    sleep_s: float = 1.0,
    api_key_env: str = "SERPAPI_KEY",
    timeout_s: int = 60,
) -> List[Dict[str, Any]]:
    """
    SerpApi Google Search (engine=google).
    Returns raw organic results items (dicts).
    Pagination uses 'start' for google search (NOT google_jobs).
    """
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing env var: {api_key_env}")

    out: List[Dict[str, Any]] = []

    for page_idx in range(max(1, int(num_pages))):
        params: Dict[str, Any] = {
            "engine": "google",
            "q": q,
            "gl": gl,
            "hl": hl,
            "api_key": api_key,
            "start": page_idx * 10,
        }

        r = requests.get(SERPAPI_URL, params=params, timeout=timeout_s)
        _raise_for_status_with_body(r)
        data = r.json()

        organic = data.get("organic_results") or []
        out.extend(organic)

        time.sleep(max(0.0, float(sleep_s)))

    return out