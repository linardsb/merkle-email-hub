"""Unit tests for ESP connector services."""

from __future__ import annotations

import pytest

from app.connectors.adobe.service import AdobeConnectorService
from app.connectors.braze.service import BrazeConnectorService
from app.connectors.protocol import ConnectorProvider
from app.connectors.sfmc.service import SFMCConnectorService
from app.connectors.taxi.service import TaxiConnectorService

# ── Protocol conformance ──


class TestProtocolConformance:
    """Verify all connector services satisfy the ConnectorProvider protocol."""

    def test_braze_is_connector_provider(self) -> None:
        assert isinstance(BrazeConnectorService(), ConnectorProvider)

    def test_sfmc_is_connector_provider(self) -> None:
        assert isinstance(SFMCConnectorService(), ConnectorProvider)

    def test_adobe_is_connector_provider(self) -> None:
        assert isinstance(AdobeConnectorService(), ConnectorProvider)

    def test_taxi_is_connector_provider(self) -> None:
        assert isinstance(TaxiConnectorService(), ConnectorProvider)


# ── Braze ──


class TestBrazeConnectorService:
    """Tests for Braze connector."""

    @pytest.fixture()
    def service(self) -> BrazeConnectorService:
        return BrazeConnectorService()

    @pytest.mark.asyncio()
    async def test_export_returns_mock_id(self, service: BrazeConnectorService) -> None:
        result = await service.export("<html></html>", "Welcome Email")
        assert result == "braze_cb_welcome_email"

    @pytest.mark.asyncio()
    async def test_package_content_block(self, service: BrazeConnectorService) -> None:
        block = await service.package_content_block("<p>Hello</p>", "Test Block")
        assert block.name == "Test Block"
        assert block.content == "<p>Hello</p>"
        assert block.content_type == "html"
        assert "email-hub" in block.tags


# ── SFMC ──


class TestSFMCConnectorService:
    """Tests for SFMC connector."""

    @pytest.fixture()
    def service(self) -> SFMCConnectorService:
        return SFMCConnectorService()

    @pytest.mark.asyncio()
    async def test_export_returns_mock_id(self, service: SFMCConnectorService) -> None:
        result = await service.export("<html></html>", "Holiday Promo")
        assert result == "sfmc_ca_holiday_promo"

    @pytest.mark.asyncio()
    async def test_package_content_area(self, service: SFMCConnectorService) -> None:
        area = await service.package_content_area("<p>SFMC content</p>", "Test Area")
        assert area.name == "Test Area"
        assert area.content == "<p>SFMC content</p>"
        assert area.content_type == "html"


# ── Adobe Campaign ──


class TestAdobeConnectorService:
    """Tests for Adobe Campaign connector."""

    @pytest.fixture()
    def service(self) -> AdobeConnectorService:
        return AdobeConnectorService()

    @pytest.mark.asyncio()
    async def test_export_returns_mock_id(self, service: AdobeConnectorService) -> None:
        result = await service.export("<html></html>", "Product Launch")
        assert result == "adobe_dl_product_launch"

    @pytest.mark.asyncio()
    async def test_package_delivery_fragment(self, service: AdobeConnectorService) -> None:
        fragment = await service.package_delivery_fragment("<p>Adobe</p>", "Test Delivery")
        assert fragment.name == "Test Delivery"
        assert fragment.content == "<p>Adobe</p>"
        assert fragment.label == "Test Delivery"


# ── Taxi for Email ──


class TestTaxiConnectorService:
    """Tests for Taxi for Email connector."""

    @pytest.fixture()
    def service(self) -> TaxiConnectorService:
        return TaxiConnectorService()

    @pytest.mark.asyncio()
    async def test_export_returns_mock_id(self, service: TaxiConnectorService) -> None:
        result = await service.export("<html></html>", "Newsletter V2")
        assert result == "taxi_tpl_newsletter_v2"

    @pytest.mark.asyncio()
    async def test_package_template_wraps_with_taxi_syntax(
        self, service: TaxiConnectorService
    ) -> None:
        template = await service.package_template("<p>Taxi</p>", "My Template")
        assert template.name == "My Template"
        assert "taxi:template" in template.content
        assert "<p>Taxi</p>" in template.content
        assert template.syntax_version == "3.0"


# ── ConnectorService dispatch ──


class TestConnectorServiceDispatch:
    """Tests for the ConnectorService provider dispatch."""

    def test_supported_connectors_has_all_four(self) -> None:
        from app.connectors.service import SUPPORTED_CONNECTORS

        assert "braze" in SUPPORTED_CONNECTORS
        assert "sfmc" in SUPPORTED_CONNECTORS
        assert "adobe_campaign" in SUPPORTED_CONNECTORS
        assert "taxi" in SUPPORTED_CONNECTORS
        assert len(SUPPORTED_CONNECTORS) == 4

    def test_unsupported_connector_raises(self) -> None:
        from unittest.mock import AsyncMock

        from app.connectors.exceptions import UnsupportedConnectorError
        from app.connectors.service import ConnectorService

        service = ConnectorService(db=AsyncMock())
        with pytest.raises(UnsupportedConnectorError, match="not supported"):
            service._get_provider("nonexistent")

    def test_get_provider_returns_correct_types(self) -> None:
        from unittest.mock import AsyncMock

        from app.connectors.service import ConnectorService

        service = ConnectorService(db=AsyncMock())
        assert isinstance(service._get_provider("braze"), BrazeConnectorService)
        assert isinstance(service._get_provider("sfmc"), SFMCConnectorService)
        assert isinstance(service._get_provider("adobe_campaign"), AdobeConnectorService)
        assert isinstance(service._get_provider("taxi"), TaxiConnectorService)

    def test_get_provider_caches_instances(self) -> None:
        from unittest.mock import AsyncMock

        from app.connectors.service import ConnectorService

        service = ConnectorService(db=AsyncMock())
        p1 = service._get_provider("braze")
        p2 = service._get_provider("braze")
        assert p1 is p2
