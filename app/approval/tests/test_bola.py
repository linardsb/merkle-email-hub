# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""BOLA authorization tests for approval endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.approval.schemas import ApprovalDecision, FeedbackCreate
from app.approval.service import ApprovalService
from app.projects.exceptions import ProjectAccessDeniedError
from app.projects.service import ProjectService


@pytest.fixture
def service() -> ApprovalService:
    mock_db = AsyncMock()
    svc = ApprovalService(mock_db)
    svc.repository = AsyncMock()
    return svc


def _make_non_member(user_id: int = 99) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.role = "developer"
    return user


def _make_approval(approval_id: int = 10, project_id: int = 1) -> MagicMock:
    approval = MagicMock()
    approval.id = approval_id
    approval.project_id = project_id
    return approval


def _deny_access() -> ProjectAccessDeniedError:
    return ProjectAccessDeniedError("Access denied")


async def test_get_approval_denied_for_non_member(service):
    service.repository.get = AsyncMock(return_value=_make_approval())
    with patch.object(ProjectService, "verify_project_access", side_effect=_deny_access()):
        with pytest.raises(ProjectAccessDeniedError):
            await service.get_approval(10, _make_non_member())


async def test_decide_denied_for_non_member(service):
    service.repository.get = AsyncMock(return_value=_make_approval())
    with patch.object(ProjectService, "verify_project_access", side_effect=_deny_access()):
        with pytest.raises(ProjectAccessDeniedError):
            decision = ApprovalDecision(status="approved")
            await service.decide(10, decision, _make_non_member())


async def test_add_feedback_denied_for_non_member(service):
    service.repository.get = AsyncMock(return_value=_make_approval())
    with patch.object(ProjectService, "verify_project_access", side_effect=_deny_access()):
        with pytest.raises(ProjectAccessDeniedError):
            data = FeedbackCreate(content="test", feedback_type="comment")
            await service.add_feedback(10, data, _make_non_member())


async def test_list_by_project_denied_for_non_member(service):
    with patch.object(ProjectService, "verify_project_access", side_effect=_deny_access()):
        with pytest.raises(ProjectAccessDeniedError):
            await service.list_by_project(1, _make_non_member())


async def test_get_feedback_denied_for_non_member(service):
    service.repository.get = AsyncMock(return_value=_make_approval())
    with patch.object(ProjectService, "verify_project_access", side_effect=_deny_access()):
        with pytest.raises(ProjectAccessDeniedError):
            await service.get_feedback(10, _make_non_member())


async def test_get_audit_trail_denied_for_non_member(service):
    service.repository.get = AsyncMock(return_value=_make_approval())
    with patch.object(ProjectService, "verify_project_access", side_effect=_deny_access()):
        with pytest.raises(ProjectAccessDeniedError):
            await service.get_audit_trail(10, _make_non_member())
