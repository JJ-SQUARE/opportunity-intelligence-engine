from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from oie.persistence.models.base import Base


class Job(Base):
    __tablename__ = "jobs"

    job_key: Mapped[str] = mapped_column(String, primary_key=True)
    job_fingerprint: Mapped[str | None] = mapped_column(String, nullable=True)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.run_id"), nullable=False)
    run_date: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    company: Mapped[str | None] = mapped_column(String, nullable=True)
    company_key: Mapped[str | None] = mapped_column(String, ForeignKey("companies.company_key"), nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    job_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    apply_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    detected_at: Mapped[str | None] = mapped_column(String, nullable=True)
    is_remote: Mapped[int] = mapped_column(Integer, default=0)
    is_contractor: Mapped[int] = mapped_column(Integer, default=0)
    is_full_time: Mapped[int] = mapped_column(Integer, default=0)
    nearshore_friendly: Mapped[int] = mapped_column(Integer, default=0)
    us_only: Mapped[int] = mapped_column(Integer, default=0)
    remote_flag: Mapped[int] = mapped_column(Integer, default=0)
    contractor_flag: Mapped[int] = mapped_column(Integer, default=0)
    many_openings_signal: Mapped[int] = mapped_column(Integer, default=0)
    offshore_mentioned: Mapped[int] = mapped_column(Integer, default=0)
    urgency_hits: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str | None] = mapped_column(String, nullable=True)
