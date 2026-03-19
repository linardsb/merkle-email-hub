"""Reporting service — orchestrates report generation with caching."""

from __future__ import annotations

import base64
import datetime
import hashlib
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.config import get_settings
from app.core.logging import get_logger
from app.reporting.exceptions import ReportNotFoundError
from app.reporting.report_builder import ReportBuilder
from app.reporting.schemas import (
    ApprovalPackageRequest,
    QAReportRequest,
    RegressionReportRequest,
    ReportDownloadResponse,
    ReportResponse,
    ReportType,
)

logger = get_logger(__name__)

# Redis key prefix
_CACHE_PREFIX = "report:"


class ReportingService:
    """Generate and cache PDF reports."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._builder = ReportBuilder(db)

    async def generate_qa_report(self, request: QAReportRequest, user: User) -> ReportResponse:
        """Generate QA report PDF, cache in Redis."""
        _ = user  # auth already enforced at route level
        pdf_bytes, filename = await self._builder.build_qa_report(request)
        return await self._cache_report(pdf_bytes, filename, ReportType.qa)

    async def generate_approval_package(
        self, request: ApprovalPackageRequest, user: User
    ) -> ReportResponse:
        """Generate approval package PDF, cache in Redis."""
        _ = user
        pdf_bytes, filename = await self._builder.build_approval_package(request)
        return await self._cache_report(pdf_bytes, filename, ReportType.approval)

    async def generate_regression_report(
        self, request: RegressionReportRequest, user: User
    ) -> ReportResponse:
        """Generate regression report PDF, cache in Redis."""
        _ = user
        pdf_bytes, filename = await self._builder.build_regression_report(request)
        return await self._cache_report(pdf_bytes, filename, ReportType.regression)

    async def get_report(self, report_id: str) -> ReportDownloadResponse:
        """Retrieve cached report by ID."""
        from app.core.redis import get_redis

        redis = await get_redis()
        key = f"{_CACHE_PREFIX}{report_id}"
        raw = await redis.get(key)
        if not raw:
            raise ReportNotFoundError(f"Report {report_id} not found or expired")

        data = json.loads(raw)
        return ReportDownloadResponse(**data)

    async def _cache_report(
        self, pdf_bytes: bytes, filename: str, report_type: ReportType
    ) -> ReportResponse:
        """Store PDF in Redis with TTL, return metadata."""
        from app.core.redis import get_redis

        settings = get_settings()
        ttl_seconds = settings.reporting.cache_ttl_h * 3600

        report_id = hashlib.sha256(pdf_bytes + filename.encode()).hexdigest()[:16]
        now = datetime.datetime.now(datetime.UTC)

        cache_data = {
            "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
            "filename": filename,
            "size_bytes": len(pdf_bytes),
            "generated_at": now.isoformat(),
        }

        redis = await get_redis()
        key = f"{_CACHE_PREFIX}{report_id}"
        await redis.set(key, json.dumps(cache_data), ex=ttl_seconds)

        logger.info(
            "report.cached",
            report_id=report_id,
            filename=filename,
            size_bytes=len(pdf_bytes),
            ttl_h=settings.reporting.cache_ttl_h,
        )

        return ReportResponse(
            report_id=report_id,
            filename=filename,
            size_bytes=len(pdf_bytes),
            generated_at=now,
            report_type=report_type,
        )
