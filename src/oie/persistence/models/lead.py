from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from oie.persistence.models.base import Base


class Lead(Base):
    __tablename__ = "leads"

    lead_key: Mapped[str] = mapped_column(String, primary_key=True)
    lead_fingerprint: Mapped[str | None] = mapped_column(String, nullable=True)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.run_id"), nullable=False)
    run_date: Mapped[str] = mapped_column(String, nullable=False)
    company_key: Mapped[str | None] = mapped_column(String, ForeignKey("companies.company_key"), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_title: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_source: Mapped[str | None] = mapped_column(String, nullable=True)
    lead_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    email_quality_score: Mapped[int] = mapped_column(Integer, default=0)
    lead_capture_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    lead_priority_label: Mapped[str | None] = mapped_column(String, nullable=True)
    lead_decision_maker_score: Mapped[float] = mapped_column(Float, default=0.0)
    lead_icp_fit_score: Mapped[float] = mapped_column(Float, default=0.0)
    lead_contact_completeness_score: Mapped[float] = mapped_column(Float, default=0.0)
    lead_penalty_negative_title: Mapped[float] = mapped_column(Float, default=0.0)
    lead_score_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_scoring_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    lead_scoring_model: Mapped[str | None] = mapped_column(String, nullable=True)
    lead_scoring_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    lead_score_title: Mapped[float] = mapped_column(Float, default=0.0)
    lead_score_source: Mapped[float] = mapped_column(Float, default=0.0)
    lead_score_email: Mapped[float] = mapped_column(Float, default=0.0)
    lead_score_linkedin: Mapped[float] = mapped_column(Float, default=0.0)
    lead_score_email_quality: Mapped[float] = mapped_column(Float, default=0.0)
    lead_score_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    lead_score_completeness_penalty: Mapped[float] = mapped_column(Float, default=0.0)
    lead_score_company_penalty: Mapped[float] = mapped_column(Float, default=0.0)
    target_persona: Mapped[str | None] = mapped_column(String, nullable=True)
    suggested_titles: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    pain_alignment: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str | None] = mapped_column(String, nullable=True)
    recommended_channel: Mapped[str | None] = mapped_column(String, nullable=True)
    lead_role_type: Mapped[str | None] = mapped_column(String, nullable=True)
    why_selected: Mapped[str | None] = mapped_column(Text, nullable=True)
    outreach_angle: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_relevance: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_or_uncertainty: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str | None] = mapped_column(String, nullable=True)
