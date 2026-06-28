from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from oie.persistence.models.base import Base


class ProviderOperationMetric(Base):
    __tablename__ = "provider_operation_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.run_id"), nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    operation: Mapped[str] = mapped_column(String, nullable=False)
    max_calls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_calls: Mapped[int] = mapped_column(Integer, default=0)
    remaining_calls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    blocked_budget: Mapped[int] = mapped_column(Integer, default=0)
    blocked_provider: Mapped[int] = mapped_column(Integer, default=0)
    errors_timeout: Mapped[int] = mapped_column(Integer, default=0)
    errors_rate_limit: Mapped[int] = mapped_column(Integer, default=0)
    errors_http_5xx: Mapped[int] = mapped_column(Integer, default=0)
    errors_execution_error: Mapped[int] = mapped_column(Integer, default=0)
    errors_auth: Mapped[int] = mapped_column(Integer, default=0)
    errors_permission: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str | None] = mapped_column(String, nullable=True)
