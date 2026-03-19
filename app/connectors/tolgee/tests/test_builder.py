"""Unit tests for locale-specific email building."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.connectors.tolgee.builder import (
    _apply_rtl,
    _is_rtl,
    build_all_locales,
    build_locale,
)


def _make_response(status_code: int = 200, **kwargs: object) -> httpx.Response:
    """Create an httpx.Response with a request set (needed for raise_for_status)."""
    request = httpx.Request("POST", "http://localhost:3001/build")
    resp = httpx.Response(status_code, request=request, **kwargs)  # type: ignore[arg-type]
    return resp


def _mock_httpx_client(response: httpx.Response) -> tuple[MagicMock, AsyncMock]:
    """Create a mock httpx.AsyncClient that works as async context manager."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm, mock_client


class TestRTLDetection:
    """Tests for RTL locale detection."""

    def test_rtl_locales(self) -> None:
        assert _is_rtl("ar") is True
        assert _is_rtl("he") is True
        assert _is_rtl("fa") is True
        assert _is_rtl("ur") is True
        assert _is_rtl("ar-SA") is True

    def test_ltr_locales(self) -> None:
        assert _is_rtl("en") is False
        assert _is_rtl("de") is False
        assert _is_rtl("ja") is False
        assert _is_rtl("zh-CN") is False


class TestApplyRTL:
    """Tests for RTL attribute injection."""

    def test_adds_dir_rtl_to_html_and_body(self) -> None:
        html = "<html><body><p>مرحبا</p></body></html>"
        result = _apply_rtl(html, "ar")
        assert 'dir="rtl"' in result
        assert result.count('dir="rtl"') == 2

    def test_no_change_for_ltr(self) -> None:
        html = "<html><body><p>Hello</p></body></html>"
        result = _apply_rtl(html, "en")
        assert result == html


class TestBuildLocale:
    """Tests for single locale build."""

    @pytest.mark.asyncio
    async def test_ltr_locale_german(self) -> None:
        """German text injected, lang="de" added."""
        source = "<html><body><td>Welcome</td></body></html>"
        translations = {"Welcome": "Willkommen"}

        response = _make_response(
            json={"html": '<html lang="de"><body><td>Willkommen</td></body></html>'}
        )
        mock_cm, _ = _mock_httpx_client(response)
        with patch("app.connectors.tolgee.builder.httpx.AsyncClient", return_value=mock_cm):
            result = await build_locale(source, translations, "de")

        assert result.locale == "de"
        assert result.text_direction == "ltr"
        assert "Willkommen" in result.html

    @pytest.mark.asyncio
    async def test_rtl_locale_arabic(self) -> None:
        """Arabic text injected, dir="rtl" applied."""
        source = "<html><body><td>Welcome</td></body></html>"
        translations = {"Welcome": "مرحبا"}

        response = _make_response(
            json={"html": '<html dir="rtl" lang="ar"><body dir="rtl"><td>مرحبا</td></body></html>'}
        )
        mock_cm, _ = _mock_httpx_client(response)
        with patch("app.connectors.tolgee.builder.httpx.AsyncClient", return_value=mock_cm):
            result = await build_locale(source, translations, "ar")

        assert result.text_direction == "rtl"
        assert result.locale == "ar"

    @pytest.mark.asyncio
    async def test_gmail_clipping_warning(self) -> None:
        """HTML >102KB triggers warning flag."""
        source = "<html><body><td>Hello</td></body></html>"
        large_html = "<html><body>" + "x" * (103 * 1024) + "</body></html>"

        response = _make_response(json={"html": large_html})
        mock_cm, _ = _mock_httpx_client(response)
        with patch("app.connectors.tolgee.builder.httpx.AsyncClient", return_value=mock_cm):
            result = await build_locale(source, {}, "en")

        assert result.gmail_clipping_warning is True

    @pytest.mark.asyncio
    async def test_html_injection_prevention(self) -> None:
        """Translated text with script tag is escaped before sending to Maizzle."""
        source = "<html><body><td>Hello</td></body></html>"
        translations = {"Hello": "<script>alert('xss')</script>"}

        response = _make_response(
            json={"html": "<html><body><td>&lt;script&gt;</td></body></html>"}
        )
        mock_cm, mock_client = _mock_httpx_client(response)
        with patch("app.connectors.tolgee.builder.httpx.AsyncClient", return_value=mock_cm):
            result = await build_locale(source, translations, "en")

        call_kwargs = mock_client.post.call_args
        sent_source = call_kwargs.kwargs["json"]["source"]
        assert "alert" in sent_source
        assert "<script>" not in result.html

    @pytest.mark.asyncio
    async def test_empty_translations_preserved(self) -> None:
        """Empty translations are skipped, source text preserved."""
        source = "<html><body><td>Original</td></body></html>"

        response = _make_response(json={"html": "<html><body><td>Original</td></body></html>"})
        mock_cm, _ = _mock_httpx_client(response)
        with patch("app.connectors.tolgee.builder.httpx.AsyncClient", return_value=mock_cm):
            result = await build_locale(source, {"Original": ""}, "de")

        assert "Original" in result.html

    @pytest.mark.asyncio
    async def test_maizzle_failure_raises(self) -> None:
        """Maizzle HTTP error raises LocaleBuildError."""
        from app.connectors.tolgee.exceptions import LocaleBuildError

        source = "<html><body></body></html>"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.HTTPError("Connection refused"))
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("app.connectors.tolgee.builder.httpx.AsyncClient", return_value=mock_cm):
            with pytest.raises(LocaleBuildError, match="Maizzle build failed"):
                await build_locale(source, {}, "en")


class TestBuildAllLocales:
    """Tests for concurrent multi-locale build."""

    @pytest.mark.asyncio
    async def test_builds_multiple_locales(self) -> None:
        """Concurrent build for 3 locales returns all results."""
        source = "<html><body><td>Hello</td></body></html>"
        locale_translations = {
            "de": {"Hello": "Hallo"},
            "fr": {"Hello": "Bonjour"},
            "es": {"Hello": "Hola"},
        }

        response = _make_response(json={"html": "<html><body><td>Translated</td></body></html>"})

        def make_mock_cm(*args: object, **kwargs: object) -> MagicMock:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=response)
            cm = MagicMock()
            cm.__aenter__ = AsyncMock(return_value=mock_client)
            cm.__aexit__ = AsyncMock(return_value=False)
            return cm

        with patch("app.connectors.tolgee.builder.httpx.AsyncClient", side_effect=make_mock_cm):
            results = await build_all_locales(source, locale_translations)

        assert len(results) == 3
        locales = {r.locale for r in results}
        assert locales == {"de", "fr", "es"}
