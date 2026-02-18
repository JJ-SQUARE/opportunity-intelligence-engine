import os
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests

SERPAPI_URL = "https://serpapi.com/search.json"

# dominios que NO queremos como “website oficial”
BLOCKLIST = (
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "ziprecruiter.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "wikipedia.org",
    "crunchbase.com",
    "bloomberg.com",
)

def _clean_domain(url: str) -> Optional[str]:
    try:
        host = (urlparse(url).hostname or "").lower()
        host = host.replace("www.", "")
        if not host:
            return None
        if any(host.endswith(d) or d in host for d in BLOCKLIST):
            return None
        return host
    except Exception:
        return None

def resolve_company_domain_serpapi(
    company_name: str,
    api_key_env: str = "SERPAPI_KEY",
    gl: str = "us",
    hl: str = "en",
    sleep_s: float = 0.5,
) -> Optional[str]:
    """
    Uses SerpApi Google Search to find the most likely official domain for a company name.
    """
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing {api_key_env} env var")

    q = f"{company_name} official website"

    params: Dict[str, Any] = {
        "engine": "google",
        "q": q,
        "api_key": api_key,
        "gl": gl,   # country
        "hl": hl,   # language
    }

    r = requests.get(SERPAPI_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    # intentar knowledge graph primero
    kg = (data.get("knowledge_graph") or {})
    if kg.get("website"):
        d = _clean_domain(kg["website"])
        if d:
            time.sleep(max(0.0, sleep_s))
            return d

    # luego resultados orgánicos
    for item in (data.get("organic_results") or [])[:8]:
        link = item.get("link")
        if not link:
            continue
        d = _clean_domain(link)
        if d:
            time.sleep(max(0.0, sleep_s))
            return d

    time.sleep(max(0.0, sleep_s))
    return None