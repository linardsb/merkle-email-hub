"""Tests for notification emitter — dedup + all event types."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.notifications.channels import Notification
from app.notifications.emitter import emit_notification
from app.notifications.tests.conftest import make_notification


def _mock_settings(enabled: bool = True) -> MagicMock:
    """Create mock settings with notifications config."""
    settings = MagicMock()
    settings.notifications.enabled = enabled
    return settings


def _mock_redis(existing_key: bool = False) -> AsyncMock:
    """Create mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value="1" if existing_key else None)
    redis.setex = AsyncMock()
    return redis


@pytest.mark.asyncio
async def test_emit_disabled() -> None:
    """notifications.enabled=False → returns False, no Redis/router calls."""
    with (
        patch("app.notifications.emitter.get_settings", return_value=_mock_settings(enabled=False)),
        patch("app.notifications.emitter.NotificationRouter") as mock_router_cls,
    ):
        result = await emit_notification(make_notification())
        assert result is False
        mock_router_cls.from_settings.assert_not_called()


@pytest.mark.asyncio
async def test_emit_blueprint_completed() -> None:
    """Mock router+redis → notify() called with blueprint.run_completed."""
    redis = _mock_redis()
    mock_router = MagicMock()
    mock_router.notify = AsyncMock(return_value=[])

    notification = make_notification(
        event="blueprint.run_completed",
        severity="info",
        title="Blueprint run completed",
        body="Blueprint run abc-123 completed (completed)",
        project_id=1,
        metadata={"run_id": "abc-123", "status": "completed"},
    )

    with (
        patch("app.notifications.emitter.get_settings", return_value=_mock_settings()),
        patch("app.core.redis.get_redis", return_value=redis),
        patch(
            "app.notifications.emitter.NotificationRouter.from_settings",
            return_value=mock_router,
        ),
    ):
        result = await emit_notification(notification)
        assert result is True
        mock_router.notify.assert_awaited_once_with(notification)


@pytest.mark.asyncio
async def test_emit_blueprint_failed() -> None:
    """Mock → notify() called with blueprint.run_failed, severity=error."""
    redis = _mock_redis()
    mock_router = MagicMock()
    mock_router.notify = AsyncMock(return_value=[])

    notification = make_notification(
        event="blueprint.run_failed",
        severity="error",
        title="Blueprint run failed",
        body="Blueprint run abc-123: needs_review",
        project_id=1,
        metadata={"run_id": "abc-123", "status": "needs_review"},
    )

    with (
        patch("app.notifications.emitter.get_settings", return_value=_mock_settings()),
        patch("app.core.redis.get_redis", return_value=redis),
        patch(
            "app.notifications.emitter.NotificationRouter.from_settings",
            return_value=mock_router,
        ),
    ):
        result = await emit_notification(notification)
        assert result is True
        mock_router.notify.assert_awaited_once()
        sent: Notification = mock_router.notify.call_args[0][0]
        assert sent.severity == "error"
        assert sent.event == "blueprint.run_failed"


@pytest.mark.asyncio
async def test_emit_qa_check_failed() -> None:
    """Mock → notify() called with qa.check_failed, failed check names in metadata."""
    redis = _mock_redis()
    mock_router = MagicMock()
    mock_router.notify = AsyncMock(return_value=[])

    notification = make_notification(
        event="qa.check_failed",
        severity="warning",
        title="QA checks failed (2)",
        body="Failed checks: html_validation, dark_mode",
        project_id=5,
        metadata={"build_id": 42, "failed_checks": ["html_validation", "dark_mode"]},
    )

    with (
        patch("app.notifications.emitter.get_settings", return_value=_mock_settings()),
        patch("app.core.redis.get_redis", return_value=redis),
        patch(
            "app.notifications.emitter.NotificationRouter.from_settings",
            return_value=mock_router,
        ),
    ):
        result = await emit_notification(notification)
        assert result is True
        sent: Notification = mock_router.notify.call_args[0][0]
        assert sent.event == "qa.check_failed"
        assert "html_validation" in sent.metadata["failed_checks"]


@pytest.mark.asyncio
async def test_emit_approval_requested() -> None:
    """Mock → notify() called with approval.requested, severity=info."""
    redis = _mock_redis()
    mock_router = MagicMock()
    mock_router.notify = AsyncMock(return_value=[])

    notification = make_notification(
        event="approval.requested",
        severity="info",
        title="Approval requested",
        body="Approval requested for build 10",
        project_id=3,
        metadata={"approval_id": 7, "build_id": 10},
    )

    with (
        patch("app.notifications.emitter.get_settings", return_value=_mock_settings()),
        patch("app.core.redis.get_redis", return_value=redis),
        patch(
            "app.notifications.emitter.NotificationRouter.from_settings",
            return_value=mock_router,
        ),
    ):
        result = await emit_notification(notification)
        assert result is True
        sent: Notification = mock_router.notify.call_args[0][0]
        assert sent.event == "approval.requested"
        assert sent.severity == "info"


@pytest.mark.asyncio
async def test_emit_approval_decided() -> None:
    """Mock → both approved (info) and rejected (warning) events."""
    redis = _mock_redis()
    mock_router = MagicMock()
    mock_router.notify = AsyncMock(return_value=[])

    for status, expected_severity in [("approved", "info"), ("rejected", "warning")]:
        redis.get = AsyncMock(return_value=None)  # Reset dedup
        notification = make_notification(
            event=f"approval.{status}",
            severity=expected_severity,
            title=f"Approval {status}",
            body=f"Approval 7 was {status}",
            project_id=3,
            metadata={"approval_id": 7, "decision": status},
        )

        with (
            patch("app.notifications.emitter.get_settings", return_value=_mock_settings()),
            patch("app.core.redis.get_redis", return_value=redis),
            patch(
                "app.notifications.emitter.NotificationRouter.from_settings",
                return_value=mock_router,
            ),
        ):
            result = await emit_notification(notification)
            assert result is True
            sent: Notification = mock_router.notify.call_args[0][0]
            assert sent.severity == expected_severity


@pytest.mark.asyncio
async def test_emit_rendering_gate_failure() -> None:
    """Mock → rendering.gate_failure with blocking clients in metadata."""
    redis = _mock_redis()
    mock_router = MagicMock()
    mock_router.notify = AsyncMock(return_value=[])

    notification = make_notification(
        event="rendering.gate_failure",
        severity="warning",
        title="Rendering confidence below threshold",
        body="Rendering gate blocked: 2 client(s) below threshold",
        project_id=1,
        metadata={"blocking_clients": ["outlook_2019", "gmail_app"]},
    )

    with (
        patch("app.notifications.emitter.get_settings", return_value=_mock_settings()),
        patch("app.core.redis.get_redis", return_value=redis),
        patch(
            "app.notifications.emitter.NotificationRouter.from_settings",
            return_value=mock_router,
        ),
    ):
        result = await emit_notification(notification)
        assert result is True
        sent: Notification = mock_router.notify.call_args[0][0]
        assert sent.event == "rendering.gate_failure"
        assert "outlook_2019" in sent.metadata["blocking_clients"]


@pytest.mark.asyncio
async def test_emit_rendering_regression() -> None:
    """Mock → rendering.regression_detected with regressions count."""
    redis = _mock_redis()
    mock_router = MagicMock()
    mock_router.notify = AsyncMock(return_value=[])

    notification = make_notification(
        event="rendering.regression_detected",
        severity="warning",
        title="Visual regression detected",
        body="3 client(s) with visual regression",
        project_id=2,
        metadata={"test_id": 99, "regressions": 3},
    )

    with (
        patch("app.notifications.emitter.get_settings", return_value=_mock_settings()),
        patch("app.core.redis.get_redis", return_value=redis),
        patch(
            "app.notifications.emitter.NotificationRouter.from_settings",
            return_value=mock_router,
        ),
    ):
        result = await emit_notification(notification)
        assert result is True
        sent: Notification = mock_router.notify.call_args[0][0]
        assert sent.event == "rendering.regression_detected"
        assert sent.metadata["regressions"] == 3


@pytest.mark.asyncio
async def test_emit_schedule_job_failed() -> None:
    """Mock → schedule.job_failed, severity=error."""
    redis = _mock_redis()
    mock_router = MagicMock()
    mock_router.notify = AsyncMock(return_value=[])

    notification = make_notification(
        event="schedule.job_failed",
        severity="error",
        title="Scheduled job failed: qa_sweep",
        body="Job qa_sweep failed: connection timeout",
        project_id=None,
        metadata={"job_name": "qa_sweep", "error": "connection timeout"},
    )

    with (
        patch("app.notifications.emitter.get_settings", return_value=_mock_settings()),
        patch("app.core.redis.get_redis", return_value=redis),
        patch(
            "app.notifications.emitter.NotificationRouter.from_settings",
            return_value=mock_router,
        ),
    ):
        result = await emit_notification(notification)
        assert result is True
        sent: Notification = mock_router.notify.call_args[0][0]
        assert sent.event == "schedule.job_failed"
        assert sent.severity == "error"
        assert sent.metadata["job_name"] == "qa_sweep"


@pytest.mark.asyncio
async def test_dedup_same_event_within_window() -> None:
    """First call → sent (True), second same event+project → skipped (False)."""
    redis_first = _mock_redis(existing_key=False)
    redis_second = _mock_redis(existing_key=True)
    mock_router = MagicMock()
    mock_router.notify = AsyncMock(return_value=[])

    notification = make_notification(event="qa.check_failed", severity="warning", project_id=5)

    # First call: not deduped
    with (
        patch("app.notifications.emitter.get_settings", return_value=_mock_settings()),
        patch("app.core.redis.get_redis", return_value=redis_first),
        patch(
            "app.notifications.emitter.NotificationRouter.from_settings",
            return_value=mock_router,
        ),
    ):
        result = await emit_notification(notification)
        assert result is True
        redis_first.setex.assert_awaited_once()

    # Second call: deduped (redis.get returns existing key)
    mock_router_2 = MagicMock()
    mock_router_2.notify = AsyncMock(return_value=[])
    with (
        patch("app.notifications.emitter.get_settings", return_value=_mock_settings()),
        patch("app.core.redis.get_redis", return_value=redis_second),
        patch(
            "app.notifications.emitter.NotificationRouter.from_settings",
            return_value=mock_router_2,
        ),
    ):
        result = await emit_notification(notification)
        assert result is False
        mock_router_2.notify.assert_not_awaited()
