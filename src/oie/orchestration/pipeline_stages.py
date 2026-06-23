from __future__ import annotations

PIPELINE_STAGES = [
    "collect_jobs",
    "company_gate",
    "freshness_gate",
    "domain_gate",
    "company_analyzer",
    "icp_match",
    "lead_generation",
    "delivery",
]

RUN_STATUSES = [
    "pending",
    "running",
    "completed",
    "partial_success",
    "failed",
    "skipped",
    "waiting_for_user",
]