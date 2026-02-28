"""Database models for test persona profiles."""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import TimestampMixin


class Persona(Base, TimestampMixin):
    """Test persona representing a subscriber profile."""

    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_client: Mapped[str] = mapped_column(String(100), nullable=False, default="gmail")
    device_type: Mapped[str] = mapped_column(String(50), nullable=False, default="desktop")
    dark_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    viewport_width: Mapped[int] = mapped_column(default=600)
    os_name: Mapped[str] = mapped_column(String(50), nullable=False, default="macOS")
    is_preset: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
