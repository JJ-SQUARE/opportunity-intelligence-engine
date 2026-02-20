from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import requests

SERPAPI_URL = "https://serpapi.com/search.json"


def serpapi_search(
    *,
    engine: str,
    params: Dict[str, Any],
    api_key_env: str = "SERPAPI_KEY",
    sleep_s: float = 0.0,
    timeout_s: int = 30,
) -> Dict[str, Any]:
    """
    Generic SerpApi search wrapper.
    - Adds engine + api_key automatically
    - Returns parsed JSON dict
    """
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing env var: {api_key_env}")

    payload = dict(params or {})
    payload["engine"] = engine
    payload["api_key"] = api_key

    r = requests.get(SERPAPI_URL, params=payload, timeout=timeout_s)
    r.raise_for_status()

    if sleep_s and sleep_s > 0:
        time.sleep(sleep_s)

    return r.json()