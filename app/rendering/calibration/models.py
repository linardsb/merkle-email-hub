"""Database models for emulator calibration."""

from sqlalchemy import JSON, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import TimestampMixin


class CalibrationRecord(Base, TimestampMixin):
    """Individual calibration measurement comparing local vs external rendering."""

    __tablename__ = "calibration_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    html_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    diff_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy_score: Mapped[float] = mapped_column(Float, nullable=False)
    pixel_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    external_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    emulator_version: Mapped[str] = mapped_column(String(64), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class CalibrationSummary(Base, TimestampMixin):
    """Aggregate calibration state per email client."""

    __tablename__ = "calibration_summaries"
    __table_args__ = (UniqueConstraint("client_id", name="uq_calibration_summary_client"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    current_accuracy: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accuracy_trend: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=list)
    known_blind_spots: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    last_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="")
