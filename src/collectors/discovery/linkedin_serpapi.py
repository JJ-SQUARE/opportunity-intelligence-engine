from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import requests
from collectors.discovery.google_search_serpapi_client import fetch_google_search_serpapi
from collectors.registry import register
# ...


SERPAPI_URL = "https://serpapi.com/search.json"


def _serpapi_google_search(
    query: str,
    api_key_env: str = "SERPAPI_KEY",
    gl: str = "us",
    hl: str = "en",
    num_pages: int = 1,
    sleep_s: float = 1.0,
    timeout: tuple[int, int] = (10, 90),  # connect/read
    retries: int = 3,
) -> List[Dict[str, Any]]:
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing env var: {api_key_env}")

    headers = {"User-Agent": "opportunity-intelligence-engine/1.0"}
    out: List[Dict[str, Any]] = []

    for page in range(num_pages):
        params: Dict[str, Any] = {
            "engine": "google",
            "q": query,
            "gl": gl,
            "hl": hl,
            "api_key": api_key,
            "start": page * 10,
        }

        last_err: Optional[Exception] = None
        for attempt in range(retries):
            try:
                r = requests.get(SERPAPI_URL, params=params, headers=headers, timeout=timeout)

                # retry on rate limit / transient
                if r.status_code in (429, 500, 502, 503, 504):
                    backoff = min(2 ** attempt, 8) + 0.25
                    print(f"[linkedin_serpapi][WARN] status={r.status_code} retry_in={backoff:.2f}s")
                    time.sleep(backoff)
                    continue

                r.raise_for_status()
                data = r.json()
                out.extend(data.get("organic_results") or [])
                last_err = None
                break

            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout) as e:
                last_err = e
                backoff = min(2 ** attempt, 8) + 0.25
                print(f"[linkedin_serpapi][WARN] timeout retry_in={backoff:.2f}s attempt={attempt+1}/{retries}")
                time.sleep(backoff)

            except requests.exceptions.RequestException as e:
                last_err = e
                backoff = min(2 ** attempt, 8) + 0.25
                print(f"[linkedin_serpapi][WARN] request_error={type(e).__name__} retry_in={backoff:.2f}s")
                time.sleep(backoff)

        if last_err is not None:
            raise last_err

        time.sleep(max(0.0, sleep_s))

    return out


@register
class LinkedInSerpApiCollector:
    name = "linkedin_serpapi"   # <- OJO: esto debe coincidir con YAML sources.discovery.linkedin_serpapi
    source = "linkedin"
    family = "discovery"

    def collect(self, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
        run_cfg = cfg.get("run", {}) or {}
        default_sleep_s = float(run_cfg.get("sleep_s", 1.0))

        c_cfg = cfg.get("collector_cfg", {}) or {}  # sources.discovery.linkedin_serpapi
        api_key_env = c_cfg.get("api_key_env", "SERPAPI_KEY")
        gl = c_cfg.get("gl", "us")
        hl = c_cfg.get("hl", "en")
        num_pages = int(c_cfg.get("num_pages", 1))
        sleep_s = float(c_cfg.get("sleep_s", default_sleep_s))

        queries = cfg.get("queries", []) or []
        out: List[Dict[str, Any]] = []

        for q in queries:
            q_name = q.get("name", "query")
            q_text = q.get("q", "")

            # Public discovery query (no login)
            search_q = f'site:linkedin.com/jobs/view "{q_text}"'

            try:
                results = fetch_google_search_serpapi(
                    query=search_q,
                    api_key_env=api_key_env,
                    gl=gl,
                    hl=hl,
                    num_pages=num_pages,
                    sleep_s=sleep_s,
                )
            except TypeError:
                results = fetch_google_search_serpapi(
                    search_q,
                    api_key_env=api_key_env,
                    gl=gl,
                    hl=hl,
                    num_pages=num_pages,
                    sleep_s=sleep_s,
                )

            for it in results:
                title = (it.get("title") or "").strip()
                job_url = it.get("link")
                snippet = it.get("snippet")

                # linkedin serp snippets don't reliably expose company; keep Unknown for now
                company = "Unknown"

                out.append(
                    {
                        "source": "linkedin",
                        "collector": self.name,
                        "company": company,
                        "title": title,
                        "job_url": job_url,
                        "description": snippet,
                        "source_id": None,
                        "source_meta": {
                            "query_name": q_name,
                            "query_text": q_text,
                            "search_query": search_q,
                        },
                        "raw": it,
                    }
                )

        return out


