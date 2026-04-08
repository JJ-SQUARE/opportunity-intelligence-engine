from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class LeadRecord:
    company_normalized: str
    company_key: Optional[str] = None
    contact_name: Optional[str] = None
    contact_title: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    lead_source: Optional[str] = None
    lead_confidence: Optional[float] = None
    email_quality_score: Optional[int] = None
    lead_capture_reason: Optional[str] = None
    lead_relevance_score: Optional[float] = None
