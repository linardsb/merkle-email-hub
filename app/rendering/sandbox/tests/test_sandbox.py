"""Integration tests for sandbox orchestrator (mocked Playwright + SMTP)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.rendering.sandbox.sandbox import send_and_capture

# Minimal email-structure HTML for test fixtures
_EMAIL_HTML = (
    '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
    'style="mso-table-lspace: 0pt; mso-table-rspace: 0pt;">'
    '<tr><td style="color: #333333; font-family: Arial, sans-serif; padding: 20px;">'
    "Hello</td></tr></table>"
)

_STRIPPED_HTML = (
    '<table role="presentation" cellpadding="0" cellspacing="0" border="0">'
    '<tr><td style="color: #333333; font-family: Arial, sans-serif; padding: 20px;">'
    "Hello</td></tr></table>"
)

_EMAIL_WITH_STYLE = (
    '<table role="presentation"><tr><td>'
    "<style>td { color: red; }</style>"
    '<table role="presentation"><tr>'
    '<td style="color: #333333;">Hello</td>'
    "</tr></table></td></tr></table>"
)

_EMAIL_WITHOUT_STYLE = (
    '<table role="presentation"><tr><td>'
    '<table role="presentation"><tr>'
    '<td style="color: #333333;">Hello</td>'
    "</tr></table></td></tr></table>"
)


@pytest.fixture(autouse=True)
def _sandbox_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENDERING__SANDBOX__ENABLED", "true")
    monkeypatch.setenv("RENDERING__SANDBOX__SMTP_HOST", "localhost")
    monkeypatch.setenv("RENDERING__SANDBOX__SMTP_PORT", "1025")
    monkeypatch.setenv("RENDERING__SANDBOX__MAILPIT_URL", "http://localhost:8025")


class TestSendAndCapture:
    @patch("app.rendering.sandbox.sandbox.send_test_email", new_callable=AsyncMock)
    @patch("app.rendering.sandbox.sandbox._wait_for_email_in_mailpit", new_callable=AsyncMock)
    @patch("app.rendering.sandbox.sandbox._capture_mailpit_html", new_callable=AsyncMock)
    async def test_mailpit_profile(
        self,
        mock_capture: AsyncMock,
        mock_wait: AsyncMock,
        mock_send: AsyncMock,
    ) -> None:
        mock_send.return_value = "<abc123@sandbox.local>"
        mock_wait.return_value = "mp-id-1"
        mock_capture.return_value = _EMAIL_HTML

        message_id, results = await send_and_capture(
            html=_EMAIL_HTML,
            subject="Test",
            profile_names=["mailpit"],
        )

        assert message_id == "<abc123@sandbox.local>"
        assert len(results) == 1
        name, rendered, screenshot, dom_diff = results[0]
        assert name == "mailpit"
        assert rendered == _EMAIL_HTML
        assert screenshot is None  # Mailpit uses API, no Playwright
        assert dom_diff is not None
        assert dom_diff.removed_elements == []  # Identical HTML

    @patch("app.rendering.sandbox.sandbox.send_test_email", new_callable=AsyncMock)
    @patch("app.rendering.sandbox.sandbox._wait_for_email_in_mailpit", new_callable=AsyncMock)
    @patch("app.rendering.sandbox.sandbox._capture_mailpit_html", new_callable=AsyncMock)
    async def test_mailpit_with_sanitizer_diff(
        self,
        mock_capture: AsyncMock,
        mock_wait: AsyncMock,
        mock_send: AsyncMock,
    ) -> None:
        mock_send.return_value = "<abc@sandbox.local>"
        mock_wait.return_value = "mp-2"
        # Simulate sanitizer stripping <style> block
        mock_capture.return_value = _EMAIL_WITHOUT_STYLE

        _message_id, results = await send_and_capture(
            html=_EMAIL_WITH_STYLE,
            subject="Test",
            profile_names=["mailpit"],
        )

        _, _, _, dom_diff = results[0]
        assert dom_diff is not None
        assert "style" in dom_diff.removed_elements

    async def test_unknown_profile_skipped(self) -> None:
        with patch(
            "app.rendering.sandbox.sandbox.send_test_email", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = "<x@sandbox.local>"
            with patch(
                "app.rendering.sandbox.sandbox._wait_for_email_in_mailpit",
                new_callable=AsyncMock,
            ) as mock_wait:
                mock_wait.return_value = "mp-3"
                _, results = await send_and_capture(
                    html=_EMAIL_HTML,
                    subject="T",
                    profile_names=["nonexistent"],
                )
                assert len(results) == 0
