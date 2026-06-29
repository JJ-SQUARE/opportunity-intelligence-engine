from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from oie.persistence.models.base import Base


class CompanyMergeCandidate(Base):
    __tablename__ = "company_merge_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.run_id"), nullable=False)
    company_key_left: Mapped[str] = mapped_column(String, nullable=False)
    company_key_right: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[str | None] = mapped_column(String, nullable=True)
