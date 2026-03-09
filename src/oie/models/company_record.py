from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class CompanyRecord:
    company_display: str
    company_normalized: str
    resolved_domain: Optional[str] = None