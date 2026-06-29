from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from oie.persistence.models.base import Base


class CompanyScore(Base):
    __tablename__ = "company_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.run_id"), nullable=False)
    company_key: Mapped[str] = mapped_column(String, ForeignKey("companies.company_key"), nullable=False)
    opportunity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    opportunity_label: Mapped[str | None] = mapped_column(String, nullable=True)
    icp_bucket: Mapped[str | None] = mapped_column(String, nullable=True)
    commercial_bucket: Mapped[str | None] = mapped_column(String, nullable=True)
    pain_urgency: Mapped[str | None] = mapped_column(String, nullable=True)
    recommended_service: Mapped[str | None] = mapped_column(String, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    score_openings: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_remote: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_contractor: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_multi_source: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_company_type: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_icp_fit: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_pain_urgency: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_region_fit: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_company_scale: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_role_seniority_mix: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_penalty_competitor: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_penalty_negative_signals: Mapped[float | None] = mapped_column(Float, nullable=True)
    primary_service_fit: Mapped[str | None] = mapped_column(String, nullable=True)
    buyer_persona_fit: Mapped[str | None] = mapped_column(String, nullable=True)
    opportunity_score_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    scoring_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    scoring_model: Mapped[str | None] = mapped_column(String, nullable=True)
    scoring_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str | None] = mapped_column(String, nullable=True)
