"""Database models for QA engine."""

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import TimestampMixin


class QAResult(Base, TimestampMixin):
    """Aggregate QA result for an email build."""

    __tablename__ = "qa_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    build_id: Mapped[int] = mapped_column(Integer, ForeignKey("email_builds.id"), nullable=False, index=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    checks_passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checks_total: Mapped[int] = mapped_column(Integer, nullable=False, default=10)


class QACheck(Base, TimestampMixin):
    """Individual QA check result."""

    __tablename__ = "qa_checks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    qa_result_id: Mapped[int] = mapped_column(Integer, ForeignKey("qa_results.id"), nullable=False, index=True)
    check_name: Mapped[str] = mapped_column(String(50), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="warning")
