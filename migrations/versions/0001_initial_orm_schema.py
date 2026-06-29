"""Initial ORM schema.

Revision ID: 0001_initial_orm_schema
Revises:
Create Date: 2026-06-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_orm_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("run_id", sa.String(), primary_key=True),
        sa.Column("run_date", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("mode", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
    )

    op.create_table(
        "companies",
        sa.Column("company_key", sa.String(), primary_key=True),
        sa.Column("company_display", sa.String(), nullable=False),
        sa.Column("company_normalized", sa.String(), nullable=False),
        sa.Column("company_root", sa.String(), nullable=True),
        sa.Column("resolved_domain", sa.String(), nullable=True),
        sa.Column("domain_source", sa.String(), nullable=True),
        sa.Column("domain_confidence", sa.Float(), nullable=True),
        sa.Column("domain_candidate", sa.String(), nullable=True),
        sa.Column("domain_validation_status", sa.String(), nullable=True),
        sa.Column("domain_review_required", sa.Integer(), nullable=True),
        sa.Column("domain_ai_validated", sa.Integer(), nullable=True),
        sa.Column("domain_ai_decision", sa.String(), nullable=True),
        sa.Column("domain_ai_confidence", sa.Float(), nullable=True),
        sa.Column("domain_ai_reason", sa.Text(), nullable=True),
        sa.Column("ai_company_identity_confidence", sa.Float(), nullable=True),
        sa.Column("ai_company_identity_source", sa.String(), nullable=True),
        sa.Column("ai_company_identity_reason", sa.Text(), nullable=True),
        sa.Column("company_identity_ai_valid", sa.Integer(), nullable=True),
        sa.Column("company_identity_ai_contaminated", sa.Integer(), nullable=True),
        sa.Column("company_identity_ai_ambiguous", sa.Integer(), nullable=True),
        sa.Column("industry", sa.String(), nullable=True),
        sa.Column("employee_range", sa.String(), nullable=True),
        sa.Column("linkedin_company_url", sa.String(), nullable=True),
        sa.Column("company_description", sa.Text(), nullable=True),
        sa.Column("company_size", sa.String(), nullable=True),
        sa.Column("enriched_at", sa.String(), nullable=True),
        sa.Column("enrichment_source", sa.String(), nullable=True),
        sa.Column("enrichment_ai_match", sa.Integer(), nullable=True),
        sa.Column("enrichment_ai_confidence", sa.Float(), nullable=True),
        sa.Column("enrichment_ai_decision", sa.String(), nullable=True),
        sa.Column("enrichment_ai_reason", sa.Text(), nullable=True),
        sa.Column("enrichment_ai_provider", sa.String(), nullable=True),
        sa.Column("enrichment_ai_model", sa.String(), nullable=True),
        sa.Column("enrichment_ai_mode", sa.String(), nullable=True),
        sa.Column("company_type_ai", sa.String(), nullable=True),
        sa.Column("classification_confidence_ai", sa.Float(), nullable=True),
        sa.Column("classification_provider", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
        sa.Column("updated_at", sa.String(), nullable=True),
    )

    op.create_table(
        "run_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("metric_key", sa.String(), nullable=False),
        sa.Column("metric_value", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
    )

    op.create_table(
        "provider_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
    )

    op.create_table(
        "provider_operation_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("max_calls", sa.Integer(), nullable=True),
        sa.Column("used_calls", sa.Integer(), nullable=True),
        sa.Column("remaining_calls", sa.Integer(), nullable=True),
        sa.Column("started", sa.Integer(), nullable=True),
        sa.Column("success", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=True),
        sa.Column("blocked_budget", sa.Integer(), nullable=True),
        sa.Column("blocked_provider", sa.Integer(), nullable=True),
        sa.Column("errors_timeout", sa.Integer(), nullable=True),
        sa.Column("errors_rate_limit", sa.Integer(), nullable=True),
        sa.Column("errors_http_5xx", sa.Integer(), nullable=True),
        sa.Column("errors_execution_error", sa.Integer(), nullable=True),
        sa.Column("errors_auth", sa.Integer(), nullable=True),
        sa.Column("errors_permission", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
    )

    op.create_table(
        "company_aliases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_key", sa.String(), sa.ForeignKey("companies.company_key"), nullable=False),
        sa.Column("alias_value", sa.String(), nullable=False),
        sa.Column("alias_normalized", sa.String(), nullable=False),
        sa.Column("alias_type", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
    )

    op.create_table(
        "domains",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_key", sa.String(), sa.ForeignKey("companies.company_key"), nullable=False),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("is_primary", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
    )

    op.create_table(
        "company_merge_candidates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("company_key_left", sa.String(), nullable=False),
        sa.Column("company_key_right", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
    )

    op.create_table(
        "jobs",
        sa.Column("job_key", sa.String(), primary_key=True),
        sa.Column("job_fingerprint", sa.String(), nullable=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("run_date", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("company", sa.String(), nullable=True),
        sa.Column("company_key", sa.String(), sa.ForeignKey("companies.company_key"), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("job_url", sa.Text(), nullable=True),
        sa.Column("apply_url", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("detected_at", sa.String(), nullable=True),
        sa.Column("is_remote", sa.Integer(), nullable=True),
        sa.Column("is_contractor", sa.Integer(), nullable=True),
        sa.Column("is_full_time", sa.Integer(), nullable=True),
        sa.Column("nearshore_friendly", sa.Integer(), nullable=True),
        sa.Column("us_only", sa.Integer(), nullable=True),
        sa.Column("remote_flag", sa.Integer(), nullable=True),
        sa.Column("contractor_flag", sa.Integer(), nullable=True),
        sa.Column("many_openings_signal", sa.Integer(), nullable=True),
        sa.Column("offshore_mentioned", sa.Integer(), nullable=True),
        sa.Column("urgency_hits", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
    )

    op.create_table(
        "leads",
        sa.Column("lead_key", sa.String(), primary_key=True),
        sa.Column("lead_fingerprint", sa.String(), nullable=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("run_date", sa.String(), nullable=False),
        sa.Column("company_key", sa.String(), sa.ForeignKey("companies.company_key"), nullable=True),
        sa.Column("contact_name", sa.String(), nullable=True),
        sa.Column("contact_title", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("linkedin_url", sa.Text(), nullable=True),
        sa.Column("lead_source", sa.String(), nullable=True),
        sa.Column("lead_confidence", sa.Float(), nullable=True),
        sa.Column("email_quality_score", sa.Integer(), nullable=True),
        sa.Column("lead_capture_reason", sa.Text(), nullable=True),
        sa.Column("lead_relevance_score", sa.Float(), nullable=True),
        sa.Column("lead_priority_label", sa.String(), nullable=True),
        sa.Column("lead_decision_maker_score", sa.Float(), nullable=True),
        sa.Column("lead_icp_fit_score", sa.Float(), nullable=True),
        sa.Column("lead_contact_completeness_score", sa.Float(), nullable=True),
        sa.Column("lead_penalty_negative_title", sa.Float(), nullable=True),
        sa.Column("lead_score_reason", sa.Text(), nullable=True),
        sa.Column("lead_scoring_provider", sa.String(), nullable=True),
        sa.Column("lead_scoring_model", sa.String(), nullable=True),
        sa.Column("lead_scoring_mode", sa.String(), nullable=True),
        sa.Column("lead_score_title", sa.Float(), nullable=True),
        sa.Column("lead_score_source", sa.Float(), nullable=True),
        sa.Column("lead_score_email", sa.Float(), nullable=True),
        sa.Column("lead_score_linkedin", sa.Float(), nullable=True),
        sa.Column("lead_score_email_quality", sa.Float(), nullable=True),
        sa.Column("lead_score_confidence", sa.Float(), nullable=True),
        sa.Column("lead_score_completeness_penalty", sa.Float(), nullable=True),
        sa.Column("lead_score_company_penalty", sa.Float(), nullable=True),
        sa.Column("target_persona", sa.String(), nullable=True),
        sa.Column("suggested_titles", sa.Text(), nullable=True),
        sa.Column("search_reason", sa.Text(), nullable=True),
        sa.Column("pain_alignment", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(), nullable=True),
        sa.Column("recommended_channel", sa.String(), nullable=True),
        sa.Column("lead_role_type", sa.String(), nullable=True),
        sa.Column("why_selected", sa.Text(), nullable=True),
        sa.Column("outreach_angle", sa.Text(), nullable=True),
        sa.Column("expected_relevance", sa.Text(), nullable=True),
        sa.Column("risk_or_uncertainty", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
    )

    op.create_table(
        "company_scores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("company_key", sa.String(), sa.ForeignKey("companies.company_key"), nullable=False),
        sa.Column("opportunity_score", sa.Float(), nullable=True),
        sa.Column("opportunity_label", sa.String(), nullable=True),
        sa.Column("icp_bucket", sa.String(), nullable=True),
        sa.Column("commercial_bucket", sa.String(), nullable=True),
        sa.Column("pain_urgency", sa.String(), nullable=True),
        sa.Column("recommended_service", sa.String(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("score_openings", sa.Float(), nullable=True),
        sa.Column("score_remote", sa.Float(), nullable=True),
        sa.Column("score_contractor", sa.Float(), nullable=True),
        sa.Column("score_multi_source", sa.Float(), nullable=True),
        sa.Column("score_company_type", sa.Float(), nullable=True),
        sa.Column("score_icp_fit", sa.Float(), nullable=True),
        sa.Column("score_pain_urgency", sa.Float(), nullable=True),
        sa.Column("score_region_fit", sa.Float(), nullable=True),
        sa.Column("score_company_scale", sa.Float(), nullable=True),
        sa.Column("score_role_seniority_mix", sa.Float(), nullable=True),
        sa.Column("score_penalty_competitor", sa.Float(), nullable=True),
        sa.Column("score_penalty_negative_signals", sa.Float(), nullable=True),
        sa.Column("primary_service_fit", sa.String(), nullable=True),
        sa.Column("buyer_persona_fit", sa.String(), nullable=True),
        sa.Column("opportunity_score_reason", sa.Text(), nullable=True),
        sa.Column("scoring_provider", sa.String(), nullable=True),
        sa.Column("scoring_model", sa.String(), nullable=True),
        sa.Column("scoring_mode", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("company_scores")
    op.drop_table("leads")
    op.drop_table("jobs")
    op.drop_table("company_merge_candidates")
    op.drop_table("domains")
    op.drop_table("company_aliases")
    op.drop_table("provider_operation_metrics")
    op.drop_table("provider_events")
    op.drop_table("run_metrics")
    op.drop_table("companies")
    op.drop_table("runs")
