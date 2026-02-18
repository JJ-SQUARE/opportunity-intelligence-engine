import os
import time
from typing import Any, Dict, List, Optional

import requests


HUNTER_DOMAIN_SEARCH_URL = "https://api.hunter.io/v2/domain-search"


def hunter_domain_search(
    domain: str,
    api_key_env: str = "HUNTER_API_KEY",
    sleep_s: float = 1.0,
    limit: int = 10,
) -> Dict[str, Any]:
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing {api_key_env} env var")

    params = {
        "domain": domain,
        "api_key": api_key,
        "limit": limit,
    }

    r = requests.get(HUNTER_DOMAIN_SEARCH_URL, params=params, timeout=30)
    r.raise_for_status()
    time.sleep(max(0.0, sleep_s))
    return r.json()


def extract_leads_from_hunter_response(company: str, domain: str, resp: Dict[str, Any]) -> List[Dict[str, Any]]:
    leads: List[Dict[str, Any]] = []

    data = (resp or {}).get("data") or {}
    emails = data.get("emails") or []

    for e in emails:
        leads.append(
            {
                "company": company,
                "domain": domain,
                "source": "hunter",
                "email": e.get("value"),
                "first_name": e.get("first_name"),
                "last_name": e.get("last_name"),
                "position": e.get("position"),
                "department": e.get("department"),
                "seniority": e.get("seniority"),
                "confidence": e.get("confidence"),
                "type": e.get("type"),
                "linkedin": e.get("linkedin"),
            }
        )

    return leads