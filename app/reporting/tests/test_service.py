"""Tests for ReportingService — business logic with Redis caching."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.reporting.exceptions import ReportNotFoundError
from app.reporting.schemas import QAReportRequest, ReportType
from app.reporting.service import ReportingService


def _mock_settings() -> MagicMock:
    settings = MagicMock()
    settings.reporting.cache_ttl_h = 24
    return settings


class TestReportingService:
    async def test_generate_qa_report_caches_to_redis(self) -> None:
        """Generated report is cached in Redis with TTL."""
        mock_db = AsyncMock()
        service = ReportingService(mock_db)

        fake_pdf = b"%PDF-1.4 content"
        service._builder.build_qa_report = AsyncMock(  # type: ignore[method-assign]
            return_value=(fake_pdf, "qa-report-42-20260318.pdf")
        )

        mock_redis = AsyncMock()
        mock_user = MagicMock()

        with (
            patch(
                "app.reporting.service.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.core.redis.get_redis",
                return_value=mock_redis,
            ),
        ):
            result = await service.generate_qa_report(QAReportRequest(qa_result_id=42), mock_user)

        assert result.filename == "qa-report-42-20260318.pdf"
        assert result.size_bytes == len(fake_pdf)
        assert result.report_type == ReportType.qa
        assert len(result.report_id) == 16

        # Verify Redis set was called with TTL
        mock_redis.set.assert_called_once()
        call_kwargs = mock_redis.set.call_args
        assert call_kwargs[1]["ex"] == 24 * 3600  # 24h TTL

    async def test_get_report_from_redis(self) -> None:
        """Cached report is retrieved from Redis."""
        mock_db = AsyncMock()
        service = ReportingService(mock_db)

        cached_data = json.dumps(
            {
                "pdf_base64": "dGVzdA==",  # base64("test")
                "filename": "qa-report-42.pdf",
                "size_bytes": 4,
                "generated_at": "2026-03-18T12:00:00",
            }
        )

        mock_redis = AsyncMock()
        mock_redis.get.return_value = cached_data

        with patch(
            "app.core.redis.get_redis",
            return_value=mock_redis,
        ):
            result = await service.get_report("abc123")

        assert result.filename == "qa-report-42.pdf"
        assert result.pdf_base64 == "dGVzdA=="
        mock_redis.get.assert_called_once_with("report:abc123")

    async def test_get_report_not_found(self) -> None:
        """Missing report raises ReportNotFoundError."""
        mock_db = AsyncMock()
        service = ReportingService(mock_db)

        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        with patch(
            "app.core.redis.get_redis",
            return_value=mock_redis,
        ):
            with pytest.raises(ReportNotFoundError, match="not found or expired"):
                await service.get_report("nonexistent")

    async def test_cache_key_deterministic(self) -> None:
        """Same content produces same cache key."""
        mock_db = AsyncMock()
        service = ReportingService(mock_db)

        fake_pdf = b"%PDF-1.4 deterministic"
        service._builder.build_qa_report = AsyncMock(  # type: ignore[method-assign]
            return_value=(fake_pdf, "qa-report-42-20260318.pdf")
        )

        mock_redis = AsyncMock()
        mock_user = MagicMock()

        report_ids: list[str] = []
        with (
            patch(
                "app.reporting.service.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.core.redis.get_redis",
                return_value=mock_redis,
            ),
        ):
            for _ in range(2):
                result = await service.generate_qa_report(
                    QAReportRequest(qa_result_id=42), mock_user
                )
                report_ids.append(result.report_id)

        assert report_ids[0] == report_ids[1]
