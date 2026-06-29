from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from oie.persistence.models.base import Base


class CompanyAlias(Base):
    __tablename__ = "company_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_key: Mapped[str] = mapped_column(String, ForeignKey("companies.company_key"), nullable=False)
    alias_value: Mapped[str] = mapped_column(String, nullable=False)
    alias_normalized: Mapped[str] = mapped_column(String, nullable=False)
    alias_type: Mapped[str | None] = mapped_column(String, default="observed_name")
    created_at: Mapped[str | None] = mapped_column(String, nullable=True)
