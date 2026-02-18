import hashlib
from typing import Any, Dict, List, Set


def _fingerprint(job: Dict[str, Any]) -> str:
    """
    Dedup fingerprint based on company/title/location/url.
    """
    raw = "|".join(
        [
            (job.get("company") or "").lower().strip(),
            (job.get("job_title") or "").lower().strip(),
            (job.get("location") or "").lower().strip(),
            (job.get("url") or "").lower().strip(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def dedupe_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Set[str] = set()
    out: List[Dict[str, Any]] = []
    for j in jobs:
        fp = _fingerprint(j)
        if fp in seen:
            continue
        seen.add(fp)
        out.append(j)
    return out