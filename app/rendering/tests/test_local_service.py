# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Unit tests for local screenshot rendering service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rendering.exceptions import (
    RenderingProviderError,
    ScreenshotRenderError,
    ScreenshotTimeoutError,
)
from app.rendering.local.profiles import CLIENT_PROFILES, RenderingProfile
from app.rendering.local.runner import _prepare_html
from app.rendering.local.service import LocalRenderingProvider
from app.rendering.protocol import RenderingProvider

# ── HTML preparation ──


class TestPrepareHtml:
    """Tests for client-specific HTML modifications."""

    def test_strip_style_tags(self) -> None:
        html = "<html><head><style>body{color:red}</style></head><body>Hi</body></html>"
        profile = RenderingProfile(
            name="gmail",
            viewport_width=680,
            viewport_height=900,
            browser="cr",
            strip_style_tags=True,
        )
        result = _prepare_html(html, profile)
        assert "<style" not in result
        assert "<body>Hi</body>" in result

    def test_strip_multiple_style_tags(self) -> None:
        html = '<style>a{}</style><style type="text/css">b{}</style><p>text</p>'
        profile = RenderingProfile(
            name="gmail",
            viewport_width=680,
            viewport_height=900,
            browser="cr",
            strip_style_tags=True,
        )
        result = _prepare_html(html, profile)
        assert "<style" not in result
        assert "<p>text</p>" in result

    def test_css_injection_before_head_close(self) -> None:
        html = "<html><head><title>T</title></head><body></body></html>"
        profile = RenderingProfile(
            name="outlook",
            viewport_width=800,
            viewport_height=900,
            browser="cr",
            css_injections=["body { max-width: 800px; }"],
        )
        result = _prepare_html(html, profile)
        assert "<style>body { max-width: 800px; }</style></head>" in result

    def test_css_injection_prepended_when_no_head(self) -> None:
        html = "<body>Hello</body>"
        profile = RenderingProfile(
            name="outlook",
            viewport_width=800,
            viewport_height=900,
            browser="cr",
            css_injections=["body { color: red; }"],
        )
        result = _prepare_html(html, profile)
        assert result.startswith("<style>body { color: red; }</style>")

    def test_strip_then_inject(self) -> None:
        """Gmail profile: strips style tags then applies emulator transforms."""
        html = "<html><head><style>.old{}</style></head><body></body></html>"
        profile = CLIENT_PROFILES["gmail_web"]
        result = _prepare_html(html, profile)
        assert ".old{}" not in result
        assert "max-width" in result  # Injected via emulator or CSS injection


# ── Client profiles ──


class TestClientProfiles:
    """Verify all 6 profiles have required fields."""

    def test_all_profiles_present(self) -> None:
        expected = {
            "gmail_web",
            "outlook_2019",
            "apple_mail",
            "outlook_dark",
            "mobile_ios",
            "outlook_web",
        }
        assert set(CLIENT_PROFILES.keys()) == expected

    def test_all_profiles_have_required_fields(self) -> None:
        for name, profile in CLIENT_PROFILES.items():
            assert profile.name == name
            assert profile.viewport_width > 0
            assert profile.viewport_height > 0
            assert profile.browser in ("cr", "wk", "ff")

    def test_apple_mail_uses_webkit(self) -> None:
        assert CLIENT_PROFILES["apple_mail"].browser == "wk"

    def test_outlook_dark_has_dark_color_scheme(self) -> None:
        assert CLIENT_PROFILES["outlook_dark"].color_scheme == "dark"

    def test_mobile_ios_has_device(self) -> None:
        assert CLIENT_PROFILES["mobile_ios"].device == "iPhone 13"

    def test_gmail_strips_styles(self) -> None:
        assert CLIENT_PROFILES["gmail_web"].strip_style_tags is True


# ── Protocol conformance ──


class TestLocalProtocolConformance:
    """Verify LocalRenderingProvider satisfies RenderingProvider protocol."""

    def test_local_is_rendering_provider(self) -> None:
        assert isinstance(LocalRenderingProvider(), RenderingProvider)

    @pytest.mark.asyncio()
    async def test_submit_returns_local_id(self) -> None:
        provider = LocalRenderingProvider()
        result = await provider.submit_test("<html></html>", "Test", ["gmail_web"])
        assert result.startswith("local_")

    @pytest.mark.asyncio()
    async def test_poll_status_always_complete(self) -> None:
        provider = LocalRenderingProvider()
        assert await provider.poll_status("local_abc") == "complete"


# ── Screenshot capture (mocked subprocess) ──


class TestCaptureScreenshot:
    """Tests for capture_screenshot with mocked subprocess."""

    @pytest.mark.asyncio()
    async def test_subprocess_called_with_correct_args(self, tmp_path: Path) -> None:
        profile = CLIENT_PROFILES["gmail_web"]
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0

        # Write a fake PNG so the file exists check passes
        output_file = tmp_path / f"{profile.name}.png"
        output_file.write_bytes(b"\x89PNG_fake")

        with (
            patch(
                "app.rendering.local.runner.asyncio.create_subprocess_exec", return_value=mock_proc
            ) as mock_exec,
            patch("app.rendering.local.runner.asyncio.wait_for", return_value=(b"", b"")),
        ):
            from app.rendering.local.runner import capture_screenshot

            result = await capture_screenshot("<html>test</html>", profile, tmp_path)

        assert result == b"\x89PNG_fake"
        # Verify subprocess was called
        mock_exec.assert_called_once()
        cmd = mock_exec.call_args[0]
        assert "playwright" in cmd[1]
        assert "--browser" in cmd
        assert "cr" in cmd
        assert "--full-page" in cmd

    @pytest.mark.asyncio()
    async def test_timeout_raises_screenshot_timeout_error(self, tmp_path: Path) -> None:
        profile = CLIENT_PROFILES["apple_mail"]
        mock_proc = AsyncMock()
        mock_proc.kill = MagicMock()

        with (
            patch(
                "app.rendering.local.runner.asyncio.create_subprocess_exec", return_value=mock_proc
            ),
            patch("app.rendering.local.runner.asyncio.wait_for", side_effect=TimeoutError),
            pytest.raises(ScreenshotTimeoutError, match="timed out"),
        ):
            from app.rendering.local.runner import capture_screenshot

            await capture_screenshot("<html></html>", profile, tmp_path)

        mock_proc.kill.assert_called_once()

    @pytest.mark.asyncio()
    async def test_nonzero_exit_raises_render_error(self, tmp_path: Path) -> None:
        profile = CLIENT_PROFILES["outlook_2019"]
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"browser crashed")
        mock_proc.returncode = 1

        with (
            patch(
                "app.rendering.local.runner.asyncio.create_subprocess_exec", return_value=mock_proc
            ),
            patch(
                "app.rendering.local.runner.asyncio.wait_for",
                return_value=(b"", b"browser crashed"),
            ),
            pytest.raises(ScreenshotRenderError, match="Playwright CLI failed"),
        ):
            from app.rendering.local.runner import capture_screenshot

            await capture_screenshot("<html></html>", profile, tmp_path)


# ── LocalRenderingProvider.render_screenshots ──


class TestRenderScreenshots:
    """Tests for the render_screenshots orchestration method."""

    @pytest.mark.asyncio()
    async def test_multiple_clients_processed(self) -> None:
        fake_bytes = b"\x89PNG_test"
        with patch(
            "app.rendering.local.service.capture_screenshot",
            new_callable=AsyncMock,
            return_value=fake_bytes,
        ):
            provider = LocalRenderingProvider()
            results = await provider.render_screenshots(
                "<html></html>", ["gmail_web", "apple_mail"]
            )

        assert len(results) == 2
        assert results[0]["client_name"] == "gmail_web"
        assert results[1]["client_name"] == "apple_mail"
        assert results[0]["image_bytes"] == fake_bytes

    @pytest.mark.asyncio()
    async def test_unknown_profile_skipped(self) -> None:
        fake_bytes = b"\x89PNG_test"
        with patch(
            "app.rendering.local.service.capture_screenshot",
            new_callable=AsyncMock,
            return_value=fake_bytes,
        ):
            provider = LocalRenderingProvider()
            results = await provider.render_screenshots(
                "<html></html>", ["gmail_web", "nonexistent"]
            )

        assert len(results) == 1
        assert results[0]["client_name"] == "gmail_web"

    @pytest.mark.asyncio()
    async def test_max_clients_enforced(self) -> None:
        fake_bytes = b"\x89PNG_test"
        all_clients = list(CLIENT_PROFILES.keys())
        with (
            patch(
                "app.rendering.local.service.capture_screenshot",
                new_callable=AsyncMock,
                return_value=fake_bytes,
            ),
            patch("app.rendering.local.service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.rendering.screenshot_max_clients = 2
            provider = LocalRenderingProvider()
            results = await provider.render_screenshots("<html></html>", all_clients)

        assert len(results) == 2

    @pytest.mark.asyncio()
    async def test_failed_capture_continues(self) -> None:
        """If one profile fails, others still render."""
        call_count = 0

        async def _mock_capture(html: str, profile: RenderingProfile, output_dir: Path) -> bytes:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ScreenshotRenderError("browser crashed")
            return b"\x89PNG_ok"

        with patch("app.rendering.local.service.capture_screenshot", side_effect=_mock_capture):
            provider = LocalRenderingProvider()
            results = await provider.render_screenshots(
                "<html></html>", ["gmail_web", "apple_mail"]
            )

        assert len(results) == 1
        assert results[0]["client_name"] == "apple_mail"


# ── RenderingService.render_screenshots ──


class TestRenderingServiceScreenshots:
    """Tests for RenderingService screenshot method."""

    @pytest.mark.asyncio()
    async def test_screenshots_disabled_raises_error(self) -> None:
        from app.rendering.service import RenderingService

        with patch("app.rendering.service.settings") as mock_settings:
            mock_settings.rendering.screenshots_enabled = False
            service = RenderingService(db=AsyncMock())
            with pytest.raises(RenderingProviderError, match="disabled"):
                from app.rendering.schemas import ScreenshotRequest

                await service.render_screenshots(
                    ScreenshotRequest(html="<html></html>", clients=["gmail_web"])
                )

    @pytest.mark.asyncio()
    async def test_screenshots_returns_base64(self) -> None:
        import base64

        from app.rendering.schemas import ScreenshotRequest
        from app.rendering.service import RenderingService

        fake_bytes = b"\x89PNG_test_data"
        mock_results = [
            {
                "client_name": "gmail_web",
                "image_bytes": fake_bytes,
                "viewport": "680x900",
                "browser": "cr",
            }
        ]

        with (
            patch("app.rendering.service.settings") as mock_settings,
            patch.object(
                LocalRenderingProvider,
                "render_screenshots",
                new_callable=AsyncMock,
                return_value=mock_results,
            ),
        ):
            mock_settings.rendering.screenshots_enabled = True
            service = RenderingService(db=AsyncMock())
            response = await service.render_screenshots(
                ScreenshotRequest(html="<html></html>", clients=["gmail_web"])
            )

        assert response.clients_rendered == 1
        assert response.clients_failed == 0
        assert response.screenshots[0].client_name == "gmail_web"
        assert response.screenshots[0].image_base64 == base64.b64encode(fake_bytes).decode("ascii")
