from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class JobRecord:
    title: str
    company: str
    location: Optional[str] = None
    job_url: Optional[str] = None
    apply_url: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    detected_at: Optional[str] = None