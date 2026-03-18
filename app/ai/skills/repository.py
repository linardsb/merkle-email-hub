"""DB CRUD for pending skill amendments."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.skills.schemas import AmendmentStatus, SkillAmendment
from app.core.database import Base
from app.core.logging import get_logger
from app.shared.models import TimestampMixin

logger = get_logger(__name__)


class SkillAmendmentRecord(TimestampMixin, Base):
    """Persisted skill amendment for review workflow."""

    __tablename__ = "skill_amendments"

    id = Column(String(12), primary_key=True)
    agent_name = Column(String(50), nullable=False, index=True)
    skill_file = Column(String(200), nullable=False)
    section = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    source_pattern_id = Column(String(12), nullable=False)
    source_template_id = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    review_reason = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)


async def save_amendments(
    db: AsyncSession,
    amendments: list[SkillAmendment],
) -> list[SkillAmendmentRecord]:
    """Persist amendments for review."""
    records = []
    for a in amendments:
        record = SkillAmendmentRecord(
            id=a.id,
            agent_name=a.agent_name,
            skill_file=a.skill_file,
            section=a.section,
            content=a.content,
            confidence=a.confidence,
            source_pattern_id=a.source_pattern_id,
            source_template_id=a.source_template_id,
            status=a.status.value,
        )
        db.add(record)
        records.append(record)
    await db.flush()
    return records


async def list_pending(
    db: AsyncSession,
    *,
    agent_name: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[SkillAmendmentRecord], int]:
    """List pending amendments, optionally filtered by agent."""
    base_filter = SkillAmendmentRecord.status == AmendmentStatus.PENDING.value
    stmt = select(SkillAmendmentRecord).where(base_filter)
    if agent_name:
        stmt = stmt.where(SkillAmendmentRecord.agent_name == agent_name)

    count_stmt = select(func.count(SkillAmendmentRecord.id)).where(base_filter)
    if agent_name:
        count_stmt = count_stmt.where(SkillAmendmentRecord.agent_name == agent_name)

    results = await db.execute(
        stmt.order_by(SkillAmendmentRecord.confidence.desc()).limit(limit).offset(offset)
    )
    count_result = await db.execute(count_stmt)
    total: int = count_result.scalar_one()

    return list(results.scalars().all()), total


async def get_amendment(db: AsyncSession, amendment_id: str) -> SkillAmendmentRecord | None:
    """Get a single amendment by ID."""
    result = await db.execute(
        select(SkillAmendmentRecord).where(SkillAmendmentRecord.id == amendment_id)
    )
    return result.scalar_one_or_none()


async def update_status(
    db: AsyncSession,
    amendment_id: str,
    status: AmendmentStatus,
    reason: str = "",
) -> SkillAmendmentRecord | None:
    """Update amendment status (approve/reject/revert)."""
    record = await get_amendment(db, amendment_id)
    if not record:
        return None
    record.status = status.value  # type: ignore[assignment]
    record.review_reason = reason  # type: ignore[assignment]
    record.reviewed_at = datetime.now(UTC)  # type: ignore[assignment]
    await db.flush()
    return record
