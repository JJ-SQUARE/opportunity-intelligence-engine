import os
import time
from typing import Any, Dict, List, Optional

import requests


HUNTER_DOMAIN_SEARCH_URL = "https://api.hunter.io/v2/domain-search"


import os
import time
from typing import Any, Dict, Optional

import requests

HUNTER_DOMAIN_SEARCH_URL = "https://api.hunter.io/v2/domain-search"


def hunter_domain_search(
    domain: str,
    api_key_env: str = "HUNTER_API_KEY",
    sleep_s: float = 1.0,
    limit: int = 10,
    retries: int = 4,
    timeout_s: int = 30,
) -> Dict[str, Any]:
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing {api_key_env} env var")

    params = {
        "domain": domain,
        "api_key": api_key,
        "limit": limit,
    }

    last_err: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            r = requests.get(HUNTER_DOMAIN_SEARCH_URL, params=params, timeout=timeout_s)
            # Si Hunter responde pero con error HTTP, lanzará aquí:
            r.raise_for_status()

            # rate-limit friendly
            if sleep_s:
                time.sleep(sleep_s)

            return r.json()

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            last_err = e
            backoff = min(2 ** attempt, 16)  # 2,4,8,16...
            print(f"[WARN] Hunter connection issue for {domain} (attempt {attempt}/{retries}): {e}. Backing off {backoff}s")
            time.sleep(backoff)
            continue

        except requests.exceptions.HTTPError as e:
            last_err = e
            status = getattr(e.response, "status_code", None)

            # 429 / 5xx -> retry
            if status in (429, 500, 502, 503, 504):
                backoff = min(2 ** attempt, 16)
                print(f"[WARN] Hunter HTTP {status} for {domain} (attempt {attempt}/{retries}). Backing off {backoff}s")
                time.sleep(backoff)
                continue

            # 4xx no-retry (ej 401 key mala, 404, 422)
            print(f"[WARN] Hunter HTTP {status} for {domain}: {e}. Skipping.")
            return {"_error": f"http_{status}", "_message": str(e), "data": {"emails": []}}

        except Exception as e:
            last_err = e
            print(f"[WARN] Hunter unexpected error for {domain}: {type(e).__name__}: {e}. Skipping.")
            return {"_error": "unexpected", "_message": str(e), "data": {"emails": []}}

    print(f"[WARN] Hunter failed after {retries} attempts for {domain}: {last_err}. Skipping.")
    return {"_error": "retries_exhausted", "_message": str(last_err), "data": {"emails": []}}


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