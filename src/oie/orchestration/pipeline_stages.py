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
    "company_classification",
    "opportunity_scoring",
    "company_limit",
    "lead_contact_generation",
    "lead_ranking",
    "lead_dedup",
    "snapshot_persistence",
    "opportunity_dataset",
    "opportunity_dataset_export",
    "outbound_export",
]

RUN_STATUSES = [
    "pending",
    "running",
    "completed",
    "partial_success",
    "failed",
    "cancelled",
    "skipped",
    "waiting_for_user",
    "company_pipeline_completed",
]

PIPELINE_STAGE_SET = set(PIPELINE_STAGES)
RUN_STATUS_SET = set(RUN_STATUSES)


def validate_pipeline_stage(stage_name: str) -> None:
    if stage_name not in PIPELINE_STAGE_SET:
        raise ValueError(f"Unknown pipeline stage: {stage_name}")


def validate_run_status(status: str) -> None:
    if status not in RUN_STATUS_SET:
        raise ValueError(f"Unknown run status: {status}")