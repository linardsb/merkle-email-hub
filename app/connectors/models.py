"""Database models for ESP connectors."""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import TimestampMixin


class ExportRecord(Base, TimestampMixin):
    """Record of an email export to an ESP."""

    __tablename__ = "export_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    build_id: Mapped[int] = mapped_column(Integer, ForeignKey("email_builds.id"), nullable=False, index=True)
    connector_type: Mapped[str] = mapped_column(String(50), nullable=False, default="braze")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    exported_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
