from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict


@dataclass
class RunMetrics:
    jobs_collected: int = 0
    jobs_after_dedupe: int = 0
    jobs_deduplicated: int = 0
    jobs_duplicates_detected: int = 0
    jobs_unique_to_append: int = 0
    companies_detected: int = 0
    companies_after_identity_dedupe: int = 0
    companies_with_domain: int = 0
    companies_enriched: int = 0
    companies_classified: int = 0
    companies_scored: int = 0
    leads_generated: int = 0
    leads_ranked: int = 0
    best_leads_selected: int = 0
    leads_duplicates_detected: int = 0
    leads_unique_to_append: int = 0
    domain_resolution_accepted: int = 0
    domain_resolution_review: int = 0
    domain_resolution_rejected: int = 0
    domain_review_queue_count: int = 0
    provider_events_count: int = 0
    run_readiness_ready: bool = False
    run_readiness_warnings: int = 0
    provider_errors: Dict[str, Dict[str, int]] = field(default_factory=dict)
    provider_blocks: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
