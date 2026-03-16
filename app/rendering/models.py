"""Database models for rendering tests."""

from sqlalchemy import ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.models import TimestampMixin


class RenderingTest(Base, TimestampMixin):
    """Record of a cross-client rendering test submission."""

    __tablename__ = "rendering_tests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    external_test_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="litmus")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    build_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("email_builds.id"), nullable=True, index=True
    )
    template_version_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("template_versions.id"), nullable=True
    )
    clients_requested: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clients_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    submitted_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    screenshots: Mapped[list["RenderingScreenshot"]] = relationship(
        back_populates="rendering_test", cascade="all, delete-orphan"
    )


class RenderingScreenshot(Base, TimestampMixin):
    """Individual client screenshot from a rendering test."""

    __tablename__ = "rendering_screenshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    rendering_test_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("rendering_tests.id"), nullable=False, index=True
    )
    client_name: Mapped[str] = mapped_column(String(100), nullable=False)
    screenshot_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    os: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    rendering_test: Mapped["RenderingTest"] = relationship(back_populates="screenshots")


class ScreenshotBaseline(Base, TimestampMixin):
    """Stored baseline screenshot for visual regression comparison."""

    __tablename__ = "screenshot_baselines"
    __table_args__ = (
        UniqueConstraint(
            "entity_type", "entity_id", "client_name", name="uq_baseline_entity_client"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    client_name: Mapped[str] = mapped_column(String(100), nullable=False)
    image_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    image_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
