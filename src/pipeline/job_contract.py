from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict

REQUIRED_FIELDS = ["title", "company", "job_url", "source", "collector"]

# Common aliases we might receive from collectors / APIs
URL_ALIASES = ["job_url", "url", "link", "listing_url"]
APPLY_URL_ALIASES = ["apply_url", "applyUrl", "application_url", "applyLink"]


def _to_dict(job: Any) -> Dict[str, Any]:
    """
    Accept either:
    - Dict[str, Any]
    - dataclass instance (e.g., JobPosting)
    """
    if isinstance(job, dict):
        return job
    if is_dataclass(job):
        return asdict(job)
    # If someone returns an object with __dict__, we can still try (optional)
    if hasattr(job, "__dict__"):
        return dict(job.__dict__)
    raise TypeError(f"Unsupported job type: {type(job).__name__}")


def _pick_first(job: Dict[str, Any], keys: list[str]) -> Any:
    for k in keys:
        v = job.get(k)
        if v:
            return v
    return None


def ensure_job_contract(job: Any, source: str, collector: str) -> Dict[str, Any]:
    """
    Enforces your standard Job schema in-place and returns job dict.

    Required (mínimos):
      - title
      - company
      - job_url
      - source
      - collector

    Optional core:
      - location
      - description
      - apply_url
      - source_id
      - source_meta (dict)
      - workplace_type
      - offer (dict)
    """
    # normalize input
    job_dict = _to_dict(job)

    # required provenance
    job_dict["source"] = job_dict.get("source") or source
    job_dict["collector"] = job_dict.get("collector") or collector

    # normalize job_url from aliases
    job_url = _pick_first(job_dict, URL_ALIASES)
    if job_url:
        job_dict["job_url"] = job_url

    # normalize apply_url from aliases
    apply_url = _pick_first(job_dict, APPLY_URL_ALIASES)
    job_dict["apply_url"] = apply_url or job_dict.get("apply_url") or None

    # defaults for optional structured fields
    if not isinstance(job_dict.get("source_meta"), dict):
        job_dict["source_meta"] = {}
    if not isinstance(job_dict.get("offer"), dict):
        job_dict["offer"] = {}

    # optional fields you asked for
    job_dict["workplace_type"] = job_dict.get("workplace_type") or None

    # soft validation
    missing = [k for k in REQUIRED_FIELDS if not job_dict.get(k)]
    if missing:
        job_dict["source_meta"]["contract_missing_fields"] = missing

    return job_dict