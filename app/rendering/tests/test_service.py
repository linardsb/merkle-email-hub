"""Unit tests for rendering test services."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.rendering.eoa.service import EoARenderingService
from app.rendering.exceptions import RenderingProviderError
from app.rendering.litmus.service import LitmusRenderingService
from app.rendering.protocol import RenderingProvider

# ── Protocol conformance ──


class TestProtocolConformance:
    """Verify all rendering services satisfy the RenderingProvider protocol."""

    def test_litmus_is_rendering_provider(self) -> None:
        assert isinstance(LitmusRenderingService(), RenderingProvider)

    def test_eoa_is_rendering_provider(self) -> None:
        assert isinstance(EoARenderingService(), RenderingProvider)


# ── Litmus ──


class TestLitmusRenderingService:
    """Tests for Litmus rendering service."""

    @pytest.fixture()
    def service(self) -> LitmusRenderingService:
        return LitmusRenderingService()

    @pytest.mark.asyncio()
    async def test_submit_test_returns_mock_id(self, service: LitmusRenderingService) -> None:
        result = await service.submit_test("<html></html>", "Test", ["gmail_web"])
        assert result.startswith("litmus_test_")

    @pytest.mark.asyncio()
    async def test_poll_status_returns_complete(self, service: LitmusRenderingService) -> None:
        result = await service.poll_status("litmus_test_12345")
        assert result == "complete"

    @pytest.mark.asyncio()
    async def test_get_results_returns_screenshots(self, service: LitmusRenderingService) -> None:
        results = await service.get_results("litmus_test_12345")
        assert len(results) == 2
        assert results[0]["client_name"] == "gmail_web"
        assert "litmus_test_12345" in results[0]["screenshot_url"]
        assert results[1]["client_name"] == "outlook_2021"


# ── Email on Acid ──


class TestEoARenderingService:
    """Tests for Email on Acid rendering service."""

    @pytest.fixture()
    def service(self) -> EoARenderingService:
        return EoARenderingService()

    @pytest.mark.asyncio()
    async def test_submit_test_returns_mock_id(self, service: EoARenderingService) -> None:
        result = await service.submit_test("<html></html>", "Test", ["gmail_web"])
        assert result.startswith("eoa_test_")

    @pytest.mark.asyncio()
    async def test_poll_status_returns_complete(self, service: EoARenderingService) -> None:
        result = await service.poll_status("eoa_test_12345")
        assert result == "complete"

    @pytest.mark.asyncio()
    async def test_get_results_returns_screenshots(self, service: EoARenderingService) -> None:
        results = await service.get_results("eoa_test_12345")
        assert len(results) == 2
        assert results[0]["client_name"] == "gmail_web"
        assert "emailonacid" in results[0]["screenshot_url"]


# ── Provider dispatch ──


class TestRenderingServiceDispatch:
    """Tests for the RenderingService provider dispatch."""

    def test_supported_providers_has_both(self) -> None:
        from app.rendering.service import SUPPORTED_PROVIDERS

        assert "litmus" in SUPPORTED_PROVIDERS
        assert "eoa" in SUPPORTED_PROVIDERS
        assert len(SUPPORTED_PROVIDERS) == 2

    def test_unsupported_provider_raises(self) -> None:
        from app.rendering.service import RenderingService

        service = RenderingService(db=AsyncMock())
        with pytest.raises(RenderingProviderError, match="not supported"):
            service._get_provider("nonexistent")

    def test_get_provider_returns_correct_types(self) -> None:
        from app.rendering.service import RenderingService

        service = RenderingService(db=AsyncMock())
        assert isinstance(service._get_provider("litmus"), LitmusRenderingService)
        assert isinstance(service._get_provider("eoa"), EoARenderingService)

    def test_get_provider_caches_instances(self) -> None:
        from app.rendering.service import RenderingService

        service = RenderingService(db=AsyncMock())
        p1 = service._get_provider("litmus")
        p2 = service._get_provider("litmus")
        assert p1 is p2
