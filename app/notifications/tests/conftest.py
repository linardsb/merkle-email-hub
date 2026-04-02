"""Test fixtures for notification tests."""

from __future__ import annotations

from typing import Any

import httpx

from app.notifications.channels import Notification


def make_notification(**overrides: Any) -> Notification:
    defaults: dict[str, Any] = {
        "event": "test.event",
        "severity": "info",
        "title": "Test notification",
        "body": "This is a test.",
        "project_id": None,
        "metadata": {},
    }
    defaults.update(overrides)
    return Notification(**defaults)


def mock_http_response(status_code: int = 200, text: str = "ok") -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        text=text,
        request=httpx.Request("POST", "http://test"),
    )
