from typing import Any, Dict, List


def normalize_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Minimal normalization: trim strings, unify empty -> None.
    """
    out = []
    for j in jobs:
        out.append(
            {
                "source": (j.get("source") or "").strip() or None,
                "job_title": (j.get("job_title") or "").strip() or None,
                "company": (j.get("company") or "").strip() or None,
                "location": (j.get("location") or "").strip() or None,
                "date_posted": (j.get("date_posted") or "").strip() or None,
                "via": (j.get("via") or "").strip() or None,
                "url": (j.get("url") or "").strip() or None,
                "description": (j.get("description") or "").strip() or None,
            }
        )
    return out