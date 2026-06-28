from __future__ import annotations

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from oie.persistence.models.base import Base


class Company(Base):
    __tablename__ = "companies"

    company_key: Mapped[str] = mapped_column(String, primary_key=True)
    company_display: Mapped[str] = mapped_column(String, nullable=False)
    company_normalized: Mapped[str] = mapped_column(String, nullable=False)
    company_root: Mapped[str | None] = mapped_column(String, nullable=True)
    resolved_domain: Mapped[str | None] = mapped_column(String, nullable=True)
    domain_source: Mapped[str | None] = mapped_column(String, nullable=True)
    domain_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    domain_candidate: Mapped[str | None] = mapped_column(String, nullable=True)
    domain_validation_status: Mapped[str | None] = mapped_column(String, nullable=True)
    domain_review_required: Mapped[int] = mapped_column(Integer, default=0)
    domain_ai_validated: Mapped[int] = mapped_column(Integer, default=0)
    domain_ai_decision: Mapped[str | None] = mapped_column(String, nullable=True)
    domain_ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    domain_ai_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_company_identity_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_company_identity_source: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_company_identity_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_identity_ai_valid: Mapped[int] = mapped_column(Integer, default=1)
    company_identity_ai_contaminated: Mapped[int] = mapped_column(Integer, default=0)
    company_identity_ai_ambiguous: Mapped[int] = mapped_column(Integer, default=0)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    employee_range: Mapped[str | None] = mapped_column(String, nullable=True)
    linkedin_company_url: Mapped[str | None] = mapped_column(String, nullable=True)
    company_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_size: Mapped[str | None] = mapped_column(String, nullable=True)
    enriched_at: Mapped[str | None] = mapped_column(String, nullable=True)
    enrichment_source: Mapped[str | None] = mapped_column(String, nullable=True)
    enrichment_ai_match: Mapped[int] = mapped_column(Integer, default=0)
    enrichment_ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    enrichment_ai_decision: Mapped[str | None] = mapped_column(String, nullable=True)
    enrichment_ai_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    enrichment_ai_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    enrichment_ai_model: Mapped[str | None] = mapped_column(String, nullable=True)
    enrichment_ai_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    company_type_ai: Mapped[str | None] = mapped_column(String, nullable=True)
    classification_confidence_ai: Mapped[float | None] = mapped_column(Float, nullable=True)
    classification_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[str | None] = mapped_column(String, nullable=True)
