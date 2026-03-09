from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class LeadRecord:
    company_normalized: str
    contact_name: Optional[str] = None
    contact_title: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None