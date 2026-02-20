from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Protocol

# Canonical dict job type used in the pipeline
Job = Dict[str, Any]


@dataclass
class JobPosting:
    """
    Canonical JobPosting schema (reference / helper).
    In the pipeline we still pass dicts (Job) to keep everything simple,
    but those dicts must conform to this schema (validated elsewhere).
    """
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
    source_meta: Dict[str, Any] = field(default_factory=dict)

    # Workplace + offer
    workplace_type: Optional[str] = None  # "remote" | "hybrid" | "onsite" | None
    offer: Dict[str, Any] = field(default_factory=dict)

    # Useful signals (optional)
    is_remote: Optional[bool] = None
    date_posted: Optional[str] = None   # ISO string if possible

    # ATS hints (optional)
    ats_type: Optional[str] = None
    ats_slug: Optional[str] = None
    domain_guess: Optional[str] = None

    # debugging
    raw: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Job:
        return asdict(self)


class Collector(Protocol):
    """
    Each collector returns List[Job] (dicts) and must be registered via @register.
    Enabled by YAML: sources.<name>.enabled = true
    """
    name: str       # key used in YAML under sources.<name>.enabled
    source: str     # "linkedin", "google_jobs", "indeed", "greenhouse", etc.
    family: str     # "job_board" | "search" | "ats" | "enterprise_ats" | "discovery"

    def collect(self, cfg: Dict[str, Any]) -> List[Job]:
        ...


class BaseCollector:
    """
    Optional convenience base class.
    Collectors can inherit to standardize attributes.
    """
    name: str = "base"
    source: str = "unknown"
    family: str = "unknown"

    def collect(self, cfg: Dict[str, Any]) -> List[Job]:
        raise NotImplementedError