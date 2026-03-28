# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""E2E tests for the EmailDesignDocument → convert → ESP push pipeline (Phase 36.7).

Tests the full flow: build an EmailDesignDocument, convert it to HTML,
then push the resulting HTML to Klaviyo and HubSpot via their sync providers.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.connectors.hubspot.sync_provider import HubSpotSyncProvider
from app.connectors.klaviyo.sync_provider import KlaviyoSyncProvider
from app.connectors.sync_schemas import ESPTemplate
from app.design_sync.converter_service import DesignConverterService
from app.design_sync.email_design_document import (
    DocumentColor,
    DocumentImage,
    DocumentLayout,
    DocumentSection,
    DocumentSource,
    DocumentText,
    DocumentTokens,
    DocumentTypography,
    EmailDesignDocument,
)

# ── Fixtures ──────────────────────────────────────────────────────────

KLAVIYO_CREDS: dict[str, str] = {"api_key": "pk_test_push_1234567890"}
HUBSPOT_CREDS: dict[str, str] = {"access_token": "pat-na1-test-push-9876"}


def _mock_response(
    status_code: int = 200,
    json_data: dict[str, Any] | list[Any] | None = None,
) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=json_data or {},
        request=httpx.Request("POST", "http://test"),
    )


def _make_document() -> EmailDesignDocument:
    return EmailDesignDocument(
        version="1.0",
        tokens=DocumentTokens(
            colors=[
                DocumentColor(name="Background", hex="#FFFFFF"),
                DocumentColor(name="Primary", hex="#0066CC"),
            ],
            typography=[
                DocumentTypography(
                    name="Body", family="Inter", weight="400", size=16.0, line_height=24.0
                ),
            ],
        ),
        sections=[
            DocumentSection(
                id="hero",
                type="hero",
                node_name="Hero",
                width=600.0,
                height=300.0,
                texts=[
                    DocumentText(
                        node_id="h1", content="Welcome Email", font_size=32.0, is_heading=True
                    ),
                ],
                images=[
                    DocumentImage(
                        node_id="img1", node_name="Hero Image", width=520.0, height=200.0
                    ),
                ],
            ),
            DocumentSection(
                id="footer",
                type="footer",
                node_name="Footer",
                width=600.0,
                height=60.0,
                texts=[
                    DocumentText(node_id="ft", content="\u00a9 2026 Acme", font_size=12.0),
                ],
            ),
        ],
        layout=DocumentLayout(container_width=600),
        source=DocumentSource(provider="figma", file_ref="test_file"),
    )


def _convert_to_html(doc: EmailDesignDocument) -> str:
    """Convert document to HTML via the converter service."""
    converter = DesignConverterService()
    result = converter.convert_document(doc)
    return result.html


# ── Klaviyo Push E2E ──────────────────────────────────────────────────


class TestKlaviyoPushE2E:
    """EmailDesignDocument → HTML → KlaviyoSyncProvider.create_template."""

    @pytest.mark.asyncio
    async def test_convert_and_push_to_klaviyo(self) -> None:
        doc = _make_document()
        html = _convert_to_html(doc)

        provider = KlaviyoSyncProvider()
        mock_resp = _mock_response(
            201,
            {
                "data": {
                    "type": "template",
                    "id": "TMPL_NEW",
                    "attributes": {
                        "name": "Welcome Email",
                        "html": html,
                        "created": "2026-03-28T00:00:00+00:00",
                        "updated": "2026-03-28T00:00:00+00:00",
                    },
                }
            },
        )

        with patch(
            "app.connectors.klaviyo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ) as mock_request:
            result = await provider.create_template("Welcome Email", html, KLAVIYO_CREDS)

        assert isinstance(result, ESPTemplate)
        assert result.id == "TMPL_NEW"
        assert result.esp_type == "klaviyo"

        # Verify the request was made with correct payload structure
        mock_request.assert_called_once()
        kwargs = mock_request.call_args.kwargs
        payload = kwargs["json"]
        assert payload["data"]["type"] == "template"
        assert payload["data"]["attributes"]["html"] == html

    @pytest.mark.asyncio
    async def test_klaviyo_receives_correct_auth_header(self) -> None:
        doc = _make_document()
        html = _convert_to_html(doc)

        provider = KlaviyoSyncProvider()
        mock_resp = _mock_response(
            201,
            {
                "data": {
                    "type": "template",
                    "id": "TMPL_2",
                    "attributes": {"name": "Test", "html": html, "created": "", "updated": ""},
                }
            },
        )

        with patch(
            "app.connectors.klaviyo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ) as mock_request:
            await provider.create_template("Test", html, KLAVIYO_CREDS)

        call_args = mock_request.call_args
        assert call_args is not None
        kwargs = call_args.kwargs
        headers = kwargs.get("headers", {})
        assert "Klaviyo-API-Key" in headers.get("Authorization", "")
        assert headers.get("revision") == "2025-07-15"

    @pytest.mark.asyncio
    async def test_klaviyo_pagination_handles_cursor(self) -> None:
        provider = KlaviyoSyncProvider()

        page1 = _mock_response(
            200,
            {
                "data": [
                    {
                        "type": "template",
                        "id": "T1",
                        "attributes": {
                            "name": "T1",
                            "html": "<p>1</p>",
                            "created": "",
                            "updated": "",
                        },
                    }
                ],
                "links": {"next": "https://a.klaviyo.com/api/templates/?page[cursor]=abc123"},
            },
        )
        page2 = _mock_response(
            200,
            {
                "data": [
                    {
                        "type": "template",
                        "id": "T2",
                        "attributes": {
                            "name": "T2",
                            "html": "<p>2</p>",
                            "created": "",
                            "updated": "",
                        },
                    }
                ],
                "links": {},
            },
        )

        with patch(
            "app.connectors.klaviyo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            side_effect=[page1, page2],
        ):
            templates = await provider.list_templates(KLAVIYO_CREDS)

        assert len(templates) == 2
        assert templates[0].id == "T1"
        assert templates[1].id == "T2"

    @pytest.mark.asyncio
    async def test_klaviyo_invalid_credentials(self) -> None:
        provider = KlaviyoSyncProvider()
        with patch(
            "app.connectors.klaviyo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPStatusError(
                "401 Unauthorized",
                request=httpx.Request("GET", "http://test"),
                response=httpx.Response(401),
            ),
        ):
            result = await provider.validate_credentials({"api_key": "bad_key"})
        assert result is False


# ── HubSpot Push E2E ──────────────────────────────────────────────────


class TestHubSpotPushE2E:
    """EmailDesignDocument → HTML → HubSpotSyncProvider.create_template."""

    @pytest.mark.asyncio
    async def test_convert_and_push_to_hubspot(self) -> None:
        doc = _make_document()
        html = _convert_to_html(doc)

        provider = HubSpotSyncProvider()
        mock_resp = _mock_response(
            200,
            {
                "id": "500",
                "name": "Welcome Email",
                "content": {"html": html},
                "type": "REGULAR",
                "createdAt": "2026-03-28T00:00:00.000Z",
                "updatedAt": "2026-03-28T00:00:00.000Z",
            },
        )

        with patch(
            "app.connectors.hubspot.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ) as mock_request:
            result = await provider.create_template("Welcome Email", html, HUBSPOT_CREDS)

        assert isinstance(result, ESPTemplate)
        assert result.id == "500"
        assert result.esp_type == "hubspot"

        # Verify correct payload
        mock_request.assert_called_once()
        kwargs = mock_request.call_args.kwargs
        payload = kwargs["json"]
        assert payload["name"] == "Welcome Email"
        assert payload["content"]["html"] == html

    @pytest.mark.asyncio
    async def test_hubspot_receives_bearer_auth(self) -> None:
        doc = _make_document()
        html = _convert_to_html(doc)

        provider = HubSpotSyncProvider()
        mock_resp = _mock_response(
            200,
            {
                "id": "501",
                "name": "Test",
                "content": {"html": html},
                "createdAt": "",
                "updatedAt": "",
            },
        )

        with patch(
            "app.connectors.hubspot.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ) as mock_request:
            await provider.create_template("Test", html, HUBSPOT_CREDS)

        call_args = mock_request.call_args
        assert call_args is not None
        kwargs = call_args.kwargs
        headers = kwargs.get("headers", {})
        assert headers.get("Authorization", "").startswith("Bearer ")

    @pytest.mark.asyncio
    async def test_hubspot_pagination_handles_after_cursor(self) -> None:
        provider = HubSpotSyncProvider()

        page1 = _mock_response(
            200,
            {
                "results": [
                    {
                        "id": "100",
                        "name": "Email 1",
                        "content": {"html": "<p>1</p>"},
                        "createdAt": "",
                        "updatedAt": "",
                    }
                ],
                "paging": {"next": {"after": "100"}},
            },
        )
        page2 = _mock_response(
            200,
            {
                "results": [
                    {
                        "id": "200",
                        "name": "Email 2",
                        "content": {"html": "<p>2</p>"},
                        "createdAt": "",
                        "updatedAt": "",
                    }
                ],
            },
        )

        with patch(
            "app.connectors.hubspot.sync_provider.resilient_request",
            new_callable=AsyncMock,
            side_effect=[page1, page2],
        ):
            templates = await provider.list_templates(HUBSPOT_CREDS)

        assert len(templates) == 2
        assert templates[0].id == "100"
        assert templates[1].id == "200"

    @pytest.mark.asyncio
    async def test_hubspot_invalid_credentials(self) -> None:
        provider = HubSpotSyncProvider()
        with patch(
            "app.connectors.hubspot.sync_provider.resilient_request",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPStatusError(
                "401 Unauthorized",
                request=httpx.Request("GET", "http://test"),
                response=httpx.Response(401),
            ),
        ):
            result = await provider.validate_credentials({"access_token": "bad_token"})
        assert result is False

    @pytest.mark.asyncio
    async def test_hubspot_update_template_with_converted_html(self) -> None:
        """Update an existing HubSpot template with freshly converted HTML."""
        doc = _make_document()
        html = _convert_to_html(doc)

        provider = HubSpotSyncProvider()
        mock_resp = _mock_response(
            200,
            {
                "id": "600",
                "name": "Updated Email",
                "content": {"html": html},
                "createdAt": "",
                "updatedAt": "2026-03-28T12:00:00.000Z",
            },
        )

        with patch(
            "app.connectors.hubspot.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            result = await provider.update_template("600", html, HUBSPOT_CREDS)

        assert isinstance(result, ESPTemplate)
        assert result.id == "600"
