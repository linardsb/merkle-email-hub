"""Unit tests for Slack, Teams, and Email notification channels."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.notifications.email_channel import EmailChannel
from app.notifications.slack import SlackChannel
from app.notifications.teams import TeamsChannel

from .conftest import make_notification, mock_http_response

# --- Slack ---


@pytest.mark.asyncio
async def test_slack_send_success() -> None:
    channel = SlackChannel(url="https://hooks.slack.com/test", timeout=5.0)
    notification = make_notification()

    with patch.object(
        httpx.AsyncClient,
        "post",
        new_callable=AsyncMock,
        return_value=mock_http_response(200),
    ):
        result = await channel.send(notification)

    assert result.success is True
    assert result.channel == "slack"
    assert result.error is None


@pytest.mark.asyncio
async def test_slack_send_failure_http() -> None:
    channel = SlackChannel(url="https://hooks.slack.com/test", timeout=5.0)
    notification = make_notification(severity="error")

    with patch.object(
        httpx.AsyncClient,
        "post",
        new_callable=AsyncMock,
        return_value=mock_http_response(500, "Internal Server Error"),
    ):
        result = await channel.send(notification)

    assert result.success is False
    assert result.channel == "slack"
    assert "500" in (result.error or "")


@pytest.mark.asyncio
async def test_slack_send_network_error() -> None:
    channel = SlackChannel(url="https://hooks.slack.com/test", timeout=5.0)
    notification = make_notification()

    with patch.object(
        httpx.AsyncClient,
        "post",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("Connection refused"),
    ):
        result = await channel.send(notification)

    assert result.success is False
    assert result.channel == "slack"
    assert result.error is not None


@pytest.mark.asyncio
async def test_slack_payload_format() -> None:
    channel = SlackChannel(url="https://hooks.slack.com/test", timeout=5.0)
    notification = make_notification(title="Build Failed", severity="error")
    captured_kwargs: dict[str, object] = {}

    async def _capture_post(url: str, **kwargs: object) -> httpx.Response:
        captured_kwargs.update(kwargs)
        return mock_http_response(200)

    with patch.object(httpx.AsyncClient, "post", side_effect=_capture_post):
        await channel.send(notification)

    payload = captured_kwargs["json"]
    assert isinstance(payload, dict)
    blocks = payload["blocks"]
    assert len(blocks) == 3
    assert blocks[0]["type"] == "header"
    assert "Build Failed" in blocks[0]["text"]["text"]
    assert blocks[1]["type"] == "section"
    assert blocks[2]["type"] == "context"


# --- Teams ---


@pytest.mark.asyncio
async def test_teams_send_success() -> None:
    channel = TeamsChannel(url="https://outlook.webhook.office.com/test", timeout=5.0)
    notification = make_notification()

    with patch.object(
        httpx.AsyncClient,
        "post",
        new_callable=AsyncMock,
        return_value=mock_http_response(200),
    ):
        result = await channel.send(notification)

    assert result.success is True
    assert result.channel == "teams"


@pytest.mark.asyncio
async def test_teams_adaptive_card_format() -> None:
    channel = TeamsChannel(url="https://outlook.webhook.office.com/test", timeout=5.0)
    notification = make_notification(title="QA Regression", severity="warning", project_id=42)
    captured_kwargs: dict[str, object] = {}

    async def _capture_post(url: str, **kwargs: object) -> httpx.Response:
        captured_kwargs.update(kwargs)
        return mock_http_response(200)

    with patch.object(httpx.AsyncClient, "post", side_effect=_capture_post):
        await channel.send(notification)

    payload = captured_kwargs["json"]
    assert isinstance(payload, dict)
    assert payload["type"] == "message"
    attachments = payload["attachments"]
    assert len(attachments) == 1
    card = attachments[0]["content"]
    assert card["type"] == "AdaptiveCard"
    body = card["body"]
    assert body[0]["text"] == "QA Regression"
    # Should include project_id in facts
    facts = body[2]["facts"]
    fact_titles = [f["title"] for f in facts]
    assert "Project" in fact_titles


# --- Email ---


@pytest.mark.asyncio
async def test_email_send_success() -> None:
    channel = EmailChannel(
        smtp_host="localhost",
        smtp_port=1025,
        from_addr="test@hub.local",
        to_addrs=["team@example.com"],
    )
    notification = make_notification()

    with patch("app.notifications.email_channel.aiosmtplib.send", new_callable=AsyncMock):
        result = await channel.send(notification)

    assert result.success is True
    assert result.channel == "email"


@pytest.mark.asyncio
async def test_email_send_smtp_error() -> None:
    import aiosmtplib

    channel = EmailChannel(
        smtp_host="localhost",
        smtp_port=1025,
        from_addr="test@hub.local",
        to_addrs=["team@example.com"],
    )
    notification = make_notification(severity="error")

    with patch(
        "app.notifications.email_channel.aiosmtplib.send",
        new_callable=AsyncMock,
        side_effect=aiosmtplib.SMTPException("Connection refused"),
    ):
        result = await channel.send(notification)

    assert result.success is False
    assert result.channel == "email"
    assert result.error is not None
