# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Data access layer for rendering tests."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.rendering.models import RenderingScreenshot, RenderingTest, ScreenshotBaseline


def _build_filters(
    *,
    build_id: int | None = None,
    template_version_id: int | None = None,
    status: str | None = None,
) -> list[ColumnElement[bool]]:
    """Build a list of SQLAlchemy filter clauses from optional parameters."""
    filters: list[ColumnElement[bool]] = []
    if build_id is not None:
        filters.append(RenderingTest.build_id == build_id)
    if template_version_id is not None:
        filters.append(RenderingTest.template_version_id == template_version_id)
    if status is not None:
        filters.append(RenderingTest.status == status)
    return filters


class RenderingRepository:
    """Database operations for rendering tests and screenshots."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_test(
        self,
        *,
        external_test_id: str,
        provider: str,
        build_id: int | None,
        template_version_id: int | None,
        clients_requested: int,
        submitted_by_id: int,
        client_names: list[str],
    ) -> RenderingTest:
        """Create a rendering test with screenshot placeholder rows."""
        test = RenderingTest(
            external_test_id=external_test_id,
            provider=provider,
            build_id=build_id,
            template_version_id=template_version_id,
            clients_requested=clients_requested,
            submitted_by_id=submitted_by_id,
            status="pending",
        )
        self.db.add(test)
        await self.db.commit()
        await self.db.refresh(test)

        for name in client_names:
            screenshot = RenderingScreenshot(
                rendering_test_id=test.id,
                client_name=name,
                status="pending",
            )
            self.db.add(screenshot)
        await self.db.commit()

        # Reload with screenshots
        return await self._get_test_eager(test.id)  # type: ignore[return-value]

    async def get_test(self, test_id: int) -> RenderingTest | None:
        """Get a rendering test by ID with screenshots eagerly loaded."""
        return await self._get_test_eager(test_id)

    async def get_test_by_external_id(self, external_id: str) -> RenderingTest | None:
        """Lookup a rendering test by the external provider's test ID."""
        result = await self.db.execute(
            select(RenderingTest)
            .where(RenderingTest.external_test_id == external_id)
            .options(selectinload(RenderingTest.screenshots))
        )
        return result.scalar_one_or_none()

    async def list_tests(
        self,
        *,
        build_id: int | None = None,
        template_version_id: int | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[RenderingTest]:
        """List rendering tests with optional filters."""
        filters = _build_filters(
            build_id=build_id, template_version_id=template_version_id, status=status
        )
        query = (
            select(RenderingTest)
            .options(selectinload(RenderingTest.screenshots))
            .where(*filters)
            .order_by(RenderingTest.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_tests(
        self,
        *,
        build_id: int | None = None,
        template_version_id: int | None = None,
        status: str | None = None,
    ) -> int:
        """Count rendering tests with optional filters."""
        filters = _build_filters(
            build_id=build_id, template_version_id=template_version_id, status=status
        )
        query = select(func.count()).select_from(RenderingTest).where(*filters)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def update_test_status(
        self,
        test_id: int,
        *,
        status: str,
        clients_completed: int | None = None,
        error_message: str | None = None,
    ) -> RenderingTest | None:
        """Update the status of a rendering test."""
        test = await self._get_test_eager(test_id)
        if not test:
            return None
        test.status = status
        if clients_completed is not None:
            test.clients_completed = clients_completed
        if error_message is not None:
            test.error_message = error_message
        await self.db.commit()
        await self.db.refresh(test)
        return test

    async def update_screenshot_status(
        self,
        screenshot_id: int,
        *,
        status: str,
        screenshot_url: str | None = None,
    ) -> RenderingScreenshot | None:
        """Update the status and URL of a single screenshot."""
        result = await self.db.execute(
            select(RenderingScreenshot).where(RenderingScreenshot.id == screenshot_id)
        )
        screenshot = result.scalar_one_or_none()
        if not screenshot:
            return None
        screenshot.status = status
        if screenshot_url is not None:
            screenshot.screenshot_url = screenshot_url
        await self.db.commit()
        await self.db.refresh(screenshot)
        return screenshot

    async def get_pending_tests(self) -> Sequence[RenderingTest]:
        """Get all tests in pending or processing status (for poller)."""
        query = (
            select(RenderingTest)
            .options(selectinload(RenderingTest.screenshots))
            .where(RenderingTest.status.in_(["pending", "processing"]))
            .order_by(RenderingTest.created_at.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _get_test_eager(self, test_id: int) -> RenderingTest | None:
        """Internal helper to load a test with screenshots."""
        result = await self.db.execute(
            select(RenderingTest)
            .where(RenderingTest.id == test_id)
            .options(selectinload(RenderingTest.screenshots))
        )
        return result.scalar_one_or_none()


class ScreenshotBaselineRepository:
    """Database operations for screenshot baselines."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_entity(
        self, entity_type: str, entity_id: int, client_name: str
    ) -> ScreenshotBaseline | None:
        result = await self.db.execute(
            select(ScreenshotBaseline).where(
                ScreenshotBaseline.entity_type == entity_type,
                ScreenshotBaseline.entity_id == entity_id,
                ScreenshotBaseline.client_name == client_name,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_entity(
        self, entity_type: str, entity_id: int
    ) -> Sequence[ScreenshotBaseline]:
        result = await self.db.execute(
            select(ScreenshotBaseline)
            .where(
                ScreenshotBaseline.entity_type == entity_type,
                ScreenshotBaseline.entity_id == entity_id,
            )
            .order_by(ScreenshotBaseline.client_name)
        )
        return list(result.scalars().all())

    async def upsert(
        self,
        *,
        entity_type: str,
        entity_id: int,
        client_name: str,
        image_data: bytes,
        image_hash: str,
        created_by_id: int,
    ) -> ScreenshotBaseline:
        existing = await self.get_by_entity(entity_type, entity_id, client_name)
        if existing:
            existing.image_data = image_data
            existing.image_hash = image_hash
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        baseline = ScreenshotBaseline(
            entity_type=entity_type,
            entity_id=entity_id,
            client_name=client_name,
            image_data=image_data,
            image_hash=image_hash,
            created_by_id=created_by_id,
        )
        self.db.add(baseline)
        await self.db.commit()
        await self.db.refresh(baseline)
        return baseline

    async def delete_by_entity(self, entity_type: str, entity_id: int) -> int:
        """Delete all baselines for an entity. Returns count deleted."""
        from sqlalchemy import delete

        result = await self.db.execute(
            delete(ScreenshotBaseline).where(
                ScreenshotBaseline.entity_type == entity_type,
                ScreenshotBaseline.entity_id == entity_id,
            )
        )
        count: int = result.rowcount  # type: ignore[attr-defined]
        if count:
            await self.db.commit()
        return count
