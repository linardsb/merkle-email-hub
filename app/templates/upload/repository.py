"""Database operations for template uploads."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.templates.upload.models import TemplateUpload


class TemplateUploadRepository:
    """CRUD operations for TemplateUpload records."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, upload: TemplateUpload) -> TemplateUpload:
        """Insert a new upload record."""
        self.db.add(upload)
        await self.db.flush()
        await self.db.refresh(upload)
        return upload

    async def get(self, upload_id: int) -> TemplateUpload | None:
        """Get upload by ID."""
        stmt = select(TemplateUpload).where(TemplateUpload.id == upload_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: int, status: str | None = None) -> list[TemplateUpload]:
        """Get uploads for a user, optionally filtered by status."""
        stmt = select(TemplateUpload).where(TemplateUpload.user_id == user_id)
        if status is not None:
            stmt = stmt.where(TemplateUpload.status == status)
        stmt = stmt.order_by(TemplateUpload.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, upload_id: int, status: str, **kwargs: object) -> None:
        """Update status and optional fields on an upload."""
        upload = await self.get(upload_id)
        if upload is None:
            return
        upload.status = status
        for key, value in kwargs.items():
            if hasattr(upload, key):
                setattr(upload, key, value)
        await self.db.flush()

    async def delete(self, upload_id: int) -> None:
        """Hard delete an upload record."""
        upload = await self.get(upload_id)
        if upload is not None:
            await self.db.delete(upload)
            await self.db.flush()

    async def count_recent_by_user(self, user_id: int, since: datetime) -> int:
        """Count uploads by a user since a given time."""
        stmt = (
            select(func.count())
            .select_from(TemplateUpload)
            .where(
                TemplateUpload.user_id == user_id,
                TemplateUpload.created_at >= since,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()
