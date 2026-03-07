"""Item database model."""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import SoftDeleteMixin, TimestampMixin


class Item(Base, TimestampMixin, SoftDeleteMixin):
    """Example item model demonstrating VSA patterns."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
