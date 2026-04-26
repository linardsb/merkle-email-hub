# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Data access layer for QA engine."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.expression import Select

from app.core.scoped_db import scoped_access
from app.qa_engine.models import QACheck, QAOverride, QAResult


def _build_filters(
    *,
    build_id: int | None = None,
    template_version_id: int | None = None,
    passed: bool | None = None,
) -> list[ColumnElement[bool]]:
    """Build a list of SQLAlchemy filter clauses from optional parameters."""
    filters: list[ColumnElement[bool]] = []
    if build_id is not None:
        filters.append(QAResult.build_id == build_id)
    if template_version_id is not None:
        filters.append(QAResult.template_version_id == template_version_id)
    if passed is not None:
        filters.append(QAResult.passed == passed)
    return filters


def _apply_project_scope(query: Select[Any], project_ids: frozenset[int]) -> Select[Any]:
    """Restrict a `QAResult` query to results whose build OR template is in scope.

    Both `build_id` and `template_version_id` are nullable; results with
    neither set are deliberately excluded for non-admin callers (admin uses
    the `None` sentinel and skips this entirely).
    """
    from app.email_engine.models import EmailBuild
    from app.templates.models import Template, TemplateVersion

    return (
        query.outerjoin(EmailBuild, EmailBuild.id == QAResult.build_id)
        .outerjoin(TemplateVersion, TemplateVersion.id == QAResult.template_version_id)
        .outerjoin(Template, Template.id == TemplateVersion.template_id)
        .where(
            or_(
                EmailBuild.project_id.in_(project_ids),
                Template.project_id.in_(project_ids),
            )
        )
    )


class QARepository:
    """Database operations for QA results and overrides."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # -- QAResult --

    async def create_result(
        self,
        *,
        build_id: int | None,
        template_version_id: int | None,
        overall_score: float,
        passed: bool,
        checks_passed: int,
        checks_total: int,
    ) -> QAResult:
        result = QAResult(
            build_id=build_id,
            template_version_id=template_version_id,
            overall_score=overall_score,
            passed=passed,
            checks_passed=checks_passed,
            checks_total=checks_total,
        )
        self.db.add(result)
        await self.db.commit()
        await self.db.refresh(result)
        return result

    async def get_result_by_id(self, result_id: int) -> QAResult | None:
        access = scoped_access(self.db)
        query = select(QAResult).where(QAResult.id == result_id)
        if access.project_ids is not None:
            query = _apply_project_scope(query, access.project_ids)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_result_with_checks(self, result_id: int) -> QAResult | None:
        """Eagerly load checks and override relationships."""
        access = scoped_access(self.db)
        query = (
            select(QAResult)
            .where(QAResult.id == result_id)
            .options(selectinload(QAResult.checks), selectinload(QAResult.override))
        )
        if access.project_ids is not None:
            query = _apply_project_scope(query, access.project_ids)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_results(
        self,
        *,
        build_id: int | None = None,
        template_version_id: int | None = None,
        passed: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[QAResult]:
        access = scoped_access(self.db)
        filters = _build_filters(
            build_id=build_id, template_version_id=template_version_id, passed=passed
        )
        query = (
            select(QAResult)
            .options(selectinload(QAResult.checks), selectinload(QAResult.override))
            .where(*filters)
            .order_by(QAResult.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if access.project_ids is not None:
            query = _apply_project_scope(query, access.project_ids)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_results(
        self,
        *,
        build_id: int | None = None,
        template_version_id: int | None = None,
        passed: bool | None = None,
    ) -> int:
        access = scoped_access(self.db)
        filters = _build_filters(
            build_id=build_id, template_version_id=template_version_id, passed=passed
        )
        query = select(func.count()).select_from(QAResult).where(*filters)
        if access.project_ids is not None:
            query = _apply_project_scope(query, access.project_ids)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_latest_result(
        self,
        *,
        build_id: int | None = None,
        template_version_id: int | None = None,
    ) -> QAResult | None:
        access = scoped_access(self.db)
        filters = _build_filters(build_id=build_id, template_version_id=template_version_id)
        query = (
            select(QAResult)
            .options(selectinload(QAResult.checks), selectinload(QAResult.override))
            .where(*filters)
            .order_by(QAResult.created_at.desc())
            .limit(1)
        )
        if access.project_ids is not None:
            query = _apply_project_scope(query, access.project_ids)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    # -- QACheck --

    async def create_checks(
        self,
        *,
        qa_result_id: int,
        checks: list[dict[str, object]],
    ) -> None:
        """Batch-insert QA check records."""
        for check_data in checks:
            qa_check = QACheck(
                qa_result_id=qa_result_id,
                check_name=check_data["check_name"],
                passed=check_data["passed"],
                score=check_data["score"],
                details=check_data.get("details"),
                severity=check_data.get("severity", "warning"),
            )
            self.db.add(qa_check)
        await self.db.commit()

    # -- QAOverride --

    async def create_override(
        self,
        *,
        qa_result_id: int,
        overridden_by_id: int,
        justification: str,
        checks_overridden: list[str],
    ) -> QAOverride:
        override = QAOverride(
            qa_result_id=qa_result_id,
            overridden_by_id=overridden_by_id,
            justification=justification,
            checks_overridden=checks_overridden,
        )
        self.db.add(override)
        await self.db.commit()
        await self.db.refresh(override)
        return override

    async def get_override_by_result_id(self, qa_result_id: int) -> QAOverride | None:
        result = await self.db.execute(
            select(QAOverride).where(QAOverride.qa_result_id == qa_result_id)
        )
        return result.scalar_one_or_none()
