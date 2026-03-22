"""Unit tests for sandbox SMTP sender (mocked — no real SMTP)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.rendering.exceptions import SandboxSMTPError
from app.rendering.sandbox.smtp import send_test_email

# Email-structure HTML for test payloads
_EMAIL_HTML = (
    '<table role="presentation" cellpadding="0" cellspacing="0" border="0">'
    '<tr><td style="color: #333333; font-family: Arial, sans-serif;">Hello</td></tr>'
    "</table>"
)


@pytest.fixture(autouse=True)
def _sandbox_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure sandbox settings for tests."""
    monkeypatch.setenv("RENDERING__SANDBOX__ENABLED", "true")
    monkeypatch.setenv("RENDERING__SANDBOX__SMTP_HOST", "localhost")
    monkeypatch.setenv("RENDERING__SANDBOX__SMTP_PORT", "1025")


class TestSendTestEmail:
    @patch("app.rendering.sandbox.smtp.aiosmtplib.send", new_callable=AsyncMock)
    async def test_send_success(self, mock_send: AsyncMock) -> None:
        mock_send.return_value = ({}, "OK")
        message_id = await send_test_email(_EMAIL_HTML, "Test Subject")
        assert message_id.startswith("<")
        assert message_id.endswith("@sandbox.local>")
        mock_send.assert_called_once()

    @patch("app.rendering.sandbox.smtp.aiosmtplib.send", new_callable=AsyncMock)
    async def test_send_failure_raises(self, mock_send: AsyncMock) -> None:
        import aiosmtplib

        mock_send.side_effect = aiosmtplib.SMTPException("Connection refused")
        with pytest.raises(SandboxSMTPError, match="Connection refused"):
            await send_test_email(_EMAIL_HTML, "Test")

    @patch("app.rendering.sandbox.smtp.aiosmtplib.send", new_callable=AsyncMock)
    async def test_custom_addresses(self, mock_send: AsyncMock) -> None:
        mock_send.return_value = ({}, "OK")
        await send_test_email(
            _EMAIL_HTML,
            "Custom",
            from_addr="custom@test.local",
            to_addr="recv@test.local",
        )
        call_args = mock_send.call_args
        msg = call_args[0][0]
        assert msg["From"] == "custom@test.local"
        assert msg["To"] == "recv@test.local"
