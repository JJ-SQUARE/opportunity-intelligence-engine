from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RunMetrics:
    jobs_collected: int = 0
    jobs_deduplicated: int = 0
    companies_detected: int = 0
    companies_with_domain: int = 0
    companies_enriched: int = 0
    leads_generated: int = 0