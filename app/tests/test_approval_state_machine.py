"""Tests for approval state machine transitions (Phase 6.4.1).

Verifies that the approval workflow enforces valid state transitions
and rejects invalid ones with 422 DomainValidationError.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.approval.exceptions import InvalidStateTransitionError
from app.approval.schemas import ApprovalDecision
from app.approval.service import ApprovalService


def _make_approval(status: str) -> MagicMock:
    """Create a mock ApprovalRequest with the given status."""
    approval = MagicMock()
    approval.id = 1
    approval.status = status
    approval.project_id = 10
    approval.build_id = 100
    approval.requested_by_id = 1
    approval.reviewed_by_id = None
    approval.review_note = None
    approval.created_at = "2026-01-01T00:00:00Z"
    approval.updated_at = "2026-01-01T00:00:00Z"
    return approval


def _make_user() -> MagicMock:
    """Create a mock User."""
    user = MagicMock()
    user.id = 1
    return user


@pytest.fixture()
def service() -> ApprovalService:
    db = AsyncMock()
    svc = ApprovalService(db)
    svc.repository = AsyncMock()
    return svc


# ── Valid transitions ──


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("pending", "approved"),
        ("pending", "rejected"),
        ("pending", "revision_requested"),
        ("revision_requested", "approved"),
        ("revision_requested", "rejected"),
        ("revision_requested", "pending"),
    ],
)
async def test_valid_transition(service: ApprovalService, current: str, target: str) -> None:
    """Valid state transitions must succeed."""
    approval = _make_approval(current)
    user = _make_user()
    updated = _make_approval(target)

    with patch.object(service, "_verify_approval_access", return_value=approval):
        mock_update = AsyncMock(return_value=updated)
        mock_audit = AsyncMock()
        service.repository.update_status = mock_update  # type: ignore[method-assign]
        service.repository.add_audit = mock_audit  # type: ignore[method-assign]

        result = await service.decide(1, ApprovalDecision(status=target), user)  # pyright: ignore[reportArgumentType]
        assert result is not None
        mock_update.assert_awaited_once()


# ── Invalid transitions ──


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("approved", "rejected"),
        ("approved", "approved"),
        ("approved", "revision_requested"),
        ("approved", "pending"),
        ("rejected", "approved"),
        ("rejected", "rejected"),
        ("rejected", "revision_requested"),
        ("rejected", "pending"),
    ],
)
async def test_invalid_transition(service: ApprovalService, current: str, target: str) -> None:
    """Invalid state transitions must raise InvalidStateTransitionError."""
    approval = _make_approval(current)
    user = _make_user()

    mock_update = AsyncMock()
    service.repository.update_status = mock_update  # type: ignore[method-assign]

    with patch.object(service, "_verify_approval_access", return_value=approval):
        with pytest.raises(InvalidStateTransitionError, match="Cannot transition"):
            await service.decide(1, ApprovalDecision(status=target), user)  # pyright: ignore[reportArgumentType]

        # Repository must NOT be called for invalid transitions
        mock_update.assert_not_awaited()
