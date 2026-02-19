from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Protocol


# -------------------------
# Canonical Job Contract
# -------------------------

@dataclass
class JobPosting:
    # Required / provenance
    source: str                 # e.g. "linkedin", "google_jobs"
    collector: str              # e.g. "linkedin_serpapi", "google_jobs_serpapi"
    company: str
    title: str
    job_url: str                # canonical job URL (listing)

    # Optional core fields
    location: Optional[str] = None
    description: Optional[str] = None
    apply_url: Optional[str] = None

    # Standard identifiers + metadata
    source_id: Optional[str] = None
    source_meta: Dict[str, Any] = field(default_factory=dict)  # free-form extra data

    # Workplace + offer (what you asked)
    workplace_type: Optional[str] = None  # "remote" | "hybrid" | "onsite" | None

    offer: Dict[str, Any] = field(default_factory=dict)
    # recommended keys inside offer (optional):
    # - employment_type: "contract" | "full_time" | "part_time" | ...
    # - contract_type: "w2" | "c2c" | "contractor" | ...
    # - rate_min / rate_max / rate_currency / rate_unit
    # - salary_min / salary_max / salary_currency / salary_unit
    # - benefits / notes

    # Useful signals (optional)
    is_remote: Optional[bool] = None
    date_posted: Optional[str] = None   # ISO string if possible

    # ATS hints (optional)
    ats_type: Optional[str] = None
    ats_slug: Optional[str] = None
    domain_guess: Optional[str] = None

    # debugging raw payload
    raw: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# -------------------------
# Collector interface
# -------------------------

class Collector(Protocol):
    name: str                   # collector key in YAML, e.g. "google_jobs"
    source: str                 # e.g. "google_jobs"
    family: str                 # e.g. "job_board" | "ats" | "discovery"

    def collect(self, cfg: Dict[str, Any]) -> List[JobPosting]:
        ...


class BaseCollector:
    """
    Implementa .collect(cfg) -> List[JobPosting]
    """
    name: str = "base"
    source: str = "unknown"
    family: str = "unknown"     # google_jobs | job_board | ats | enterprise_ats | discovery

    def collect(self, cfg: Dict[str, Any]) -> List[JobPosting]:
        raise NotImplementedError