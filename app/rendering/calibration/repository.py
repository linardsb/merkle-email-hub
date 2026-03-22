# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Data access layer for emulator calibration."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rendering.calibration.models import CalibrationRecord, CalibrationSummary


class CalibrationRepository:
    """Database operations for calibration records and summaries."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_record(self, **kwargs: object) -> CalibrationRecord:
        """Create a new calibration measurement record."""
        record = CalibrationRecord(**kwargs)
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def list_records(
        self, client_id: str, *, limit: int = 20, offset: int = 0
    ) -> Sequence[CalibrationRecord]:
        """List calibration records for a client, newest first."""
        result = await self.db.execute(
            select(CalibrationRecord)
            .where(CalibrationRecord.client_id == client_id)
            .order_by(CalibrationRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_records(self, client_id: str) -> int:
        """Count total calibration records for a client."""
        result = await self.db.execute(
            select(func.count())
            .select_from(CalibrationRecord)
            .where(CalibrationRecord.client_id == client_id)
        )
        return result.scalar_one()

    async def count_today(self, client_id: str) -> int:
        """Count calibration records created today for a client."""
        result = await self.db.execute(
            select(func.count())
            .select_from(CalibrationRecord)
            .where(
                CalibrationRecord.client_id == client_id,
                func.date(CalibrationRecord.created_at) == func.current_date(),
            )
        )
        return result.scalar_one()

    async def get_summary(self, client_id: str) -> CalibrationSummary | None:
        """Get the calibration summary for a client."""
        result = await self.db.execute(
            select(CalibrationSummary).where(CalibrationSummary.client_id == client_id)
        )
        return result.scalar_one_or_none()

    async def list_summaries(self) -> Sequence[CalibrationSummary]:
        """List all calibration summaries, ordered by client_id."""
        result = await self.db.execute(
            select(CalibrationSummary).order_by(CalibrationSummary.client_id)
        )
        return list(result.scalars().all())

    async def upsert_summary(self, **kwargs: object) -> CalibrationSummary:
        """Create or update a calibration summary for a client."""
        client_id = str(kwargs["client_id"])
        existing = await self.get_summary(client_id)
        if existing:
            for key, value in kwargs.items():
                if key != "client_id":
                    setattr(existing, key, value)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        summary = CalibrationSummary(**kwargs)
        self.db.add(summary)
        await self.db.commit()
        await self.db.refresh(summary)
        return summary
