from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class DomainRecord:
    company_normalized: str
    domain: str
    source: Optional[str] = None
    confidence: Optional[float] = None