"""Unit tests for NotificationRouter."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.config import NotificationsConfig
from app.notifications.channels import Notification, NotificationResult
from app.notifications.router import NotificationRouter

from .conftest import make_notification


class _MockChannel:
    """Minimal channel for testing router dispatch."""

    def __init__(self, channel_name: str, *, fail: bool = False, raise_exc: bool = False) -> None:
        self._name = channel_name
        self._fail = fail
        self._raise_exc = raise_exc
        self.send = AsyncMock(side_effect=self._send)

    @property
    def name(self) -> str:
        return self._name

    async def _send(self, notification: Notification) -> NotificationResult:
        if self._raise_exc:
            msg = "boom"
            raise RuntimeError(msg)
        return NotificationResult(
            channel=self._name,
            success=not self._fail,
            error="simulated failure" if self._fail else None,
        )


def test_from_settings_no_channels() -> None:
    config = NotificationsConfig()
    router = NotificationRouter.from_settings(config)
    assert len(router._channels) == 0


def test_from_settings_slack_only() -> None:
    config = NotificationsConfig(
        slack_enabled=True,
        slack_webhook_url="https://hooks.slack.com/test",
    )
    router = NotificationRouter.from_settings(config)
    assert len(router._channels) == 1
    assert router._channels[0].name == "slack"


def test_from_settings_all_channels() -> None:
    config = NotificationsConfig(
        slack_enabled=True,
        slack_webhook_url="https://hooks.slack.com/test",
        teams_enabled=True,
        teams_webhook_url="https://outlook.webhook.office.com/test",
        email_enabled=True,
        email_smtp_host="localhost",
        email_to_addrs=["team@example.com"],
    )
    router = NotificationRouter.from_settings(config)
    assert len(router._channels) == 3


@pytest.mark.asyncio
async def test_notify_broadcasts_to_all() -> None:
    ch1 = _MockChannel("ch1")
    ch2 = _MockChannel("ch2")
    router = NotificationRouter([ch1, ch2])
    notification = make_notification()

    results = await router.notify(notification)

    assert len(results) == 2
    ch1.send.assert_awaited_once_with(notification)
    ch2.send.assert_awaited_once_with(notification)


@pytest.mark.asyncio
async def test_notify_channel_failure_continues() -> None:
    ch1 = _MockChannel("ch1", raise_exc=True)
    ch2 = _MockChannel("ch2")
    router = NotificationRouter([ch1, ch2])
    notification = make_notification()

    results = await router.notify(notification)

    assert len(results) == 2
    assert results[0].success is False
    assert results[1].success is True
    ch2.send.assert_awaited_once_with(notification)


@pytest.mark.asyncio
async def test_notify_returns_results() -> None:
    ch1 = _MockChannel("ch1")
    ch2 = _MockChannel("ch2", fail=True)
    router = NotificationRouter([ch1, ch2])
    notification = make_notification()

    results = await router.notify(notification)

    assert len(results) == 2
    assert results[0].success is True
    assert results[1].success is False
    assert results[1].error == "simulated failure"
