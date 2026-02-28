"""Database models for email build pipeline."""

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import TimestampMixin


class EmailBuild(Base, TimestampMixin):
    """Record of an email build execution."""

    __tablename__ = "email_builds"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=False, index=True
    )
    template_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    source_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    compiled_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    build_config: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    is_production: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
