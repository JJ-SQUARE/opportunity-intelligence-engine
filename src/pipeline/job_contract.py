from __future__ import annotations
from typing import Any, Dict, Optional
from urllib.parse import urlparse


WORKPLACE_ALIASES = {
    "remote": "remote",
    "remoto": "remote",
    "hybrid": "hybrid",
    "híbrido": "hybrid",
    "onsite": "onsite",
    "on-site": "onsite",
    "presencial": "onsite",
}

def _norm_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip()
    return s or None

def _norm_url(u: Any) -> Optional[str]:
    u = _norm_str(u)
    if not u:
        return None
    try:
        p = urlparse(u)
        if not p.scheme or not p.netloc:
            return None
        return u
    except Exception:
        return None

def _norm_workplace_type(x: Any) -> Optional[str]:
    s = (_norm_str(x) or "").lower()
    if not s:
        return None
    return WORKPLACE_ALIASES.get(s, s)  # deja pasar otros si llegan

def ensure_job_contract(job: Dict[str, Any], *, source: str, collector: str) -> Dict[str, Any]:
    """
    Enforce Job v1 contract. Mutates and returns job.
    Always sets source/collector, always ensures offer dict, source_meta dict.
    """
    job["title"] = _norm_str(job.get("title"))
    job["company"] = _norm_str(job.get("company"))
    job["location"] = _norm_str(job.get("location"))
    job["description"] = _norm_str(job.get("description"))

    job["job_url"] = _norm_url(job.get("job_url") or job.get("url") or job.get("link"))
    job["apply_url"] = _norm_url(job.get("apply_url"))

    job["source"] = _norm_str(job.get("source")) or source
    job["collector"] = _norm_str(job.get("collector")) or collector

    job["source_id"] = _norm_str(job.get("source_id"))
    job["source_meta"] = job.get("source_meta") or {}
    if not isinstance(job["source_meta"], dict):
        job["source_meta"] = {"raw_source_meta": job["source_meta"]}

    job["workplace_type"] = _norm_workplace_type(job.get("workplace_type"))

    offer = job.get("offer") or {}
    if not isinstance(offer, dict):
        offer = {"raw_offer": offer}
    # no obligamos campos adentro, pero aseguramos dict
    job["offer"] = offer

    return job