import os
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests

SERPAPI_URL = "https://serpapi.com/search.json"

# dominios que NO queremos como “website oficial”
BLOCKLIST = {
    "linkedin.com", "indeed.com", "glassdoor.com", "ziprecruiter.com",
    "facebook.com", "twitter.com", "x.com", "instagram.com",
    "wikipedia.org", "crunchbase.com", "bloomberg.com",
    "dice.com", "nofluffjobs.com", "workable.com",
    "greenhouse.io", "lever.co", "ashbyhq.com",
    "myworkdayjobs.com", "taleo.net", "icims.com",
}

COMMON_SUBDOMAINS = {"jobs", "careers", "boards", "apply", "join"}


def _is_blocked(host: str) -> bool:
    host = (host or "").lower().strip()
    for d in BLOCKLIST:
        if host == d:
            return True
        if host.endswith("." + d):
            return True
    return False

def is_blocked_domain(domain: str) -> bool:
    d = (domain or "").lower().strip()
    d = d.replace("https://", "").replace("http://", "").split("/")[0]
    d = d.replace("www.", "")
    for b in BLOCKLIST:
        if d == b or d.endswith("." + b):
            return True
    return False

def _clean_domain(url: str) -> Optional[str]:
    try:
        host = (urlparse(url).hostname or "").lower().strip()
        if not host:
            return None

        # normalize
        if host.startswith("www."):
            host = host[4:]

        # drop common job subdomains (keeps company base domain)
        parts = host.split(".")
        if len(parts) >= 3 and parts[0] in COMMON_SUBDOMAINS:
            host = ".".join(parts[1:])

        # blocklist (exact or subdomain)
        if _is_blocked(host):
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

    queries = [
        f"{company_name} official website",
        f"{company_name} website",
    ]

    for q in queries:
        params: Dict[str, Any] = {
            "engine": "google",
            "q": q,
            "api_key": api_key,
            "gl": gl,
            "hl": hl,
        }

        r = requests.get(SERPAPI_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        # knowledge graph first
        kg = (data.get("knowledge_graph") or {})
        if kg.get("website"):
            d = _clean_domain(kg["website"])
            if d:
                time.sleep(max(0.0, sleep_s))
                return d

        # organic results fallback
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