"""SQLAlchemy model for template upload state."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import TimestampMixin


class TemplateUpload(Base, TimestampMixin):
    """Tracks an uploaded template through the analysis -> review -> confirm pipeline."""

    __tablename__ = "template_uploads"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_review")
    original_html: Mapped[str] = mapped_column(Text, nullable=False)
    sanitized_html: Mapped[str] = mapped_column(Text, nullable=False)
    analysis_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    confirmed_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    esp_platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
