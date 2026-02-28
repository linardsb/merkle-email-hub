"""Database models for client approval portal."""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import SoftDeleteMixin, TimestampMixin


class ApprovalRequest(Base, TimestampMixin, SoftDeleteMixin):
    """Approval request for a built email template."""

    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    build_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("email_builds.id"), nullable=False, index=True
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    requested_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    reviewed_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Feedback(Base, TimestampMixin):
    """Feedback comment on an approval request."""

    __tablename__ = "approval_feedback"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    approval_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("approval_requests.id"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_type: Mapped[str] = mapped_column(String(20), nullable=False, default="comment")


class AuditEntry(Base, TimestampMixin):
    """Time-stamped audit trail entry for approval workflow."""

    __tablename__ = "approval_audit"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    approval_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("approval_requests.id"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
