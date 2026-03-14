# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""BOLA authorization tests for project endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.projects.exceptions import ProjectAccessDeniedError
from app.projects.schemas import ProjectUpdate
from app.projects.service import ProjectService


@pytest.fixture
def service() -> ProjectService:
    mock_db = AsyncMock()
    svc = ProjectService(mock_db)
    svc.projects = AsyncMock()
    svc.orgs = AsyncMock()
    return svc


def _make_project(project_id: int = 1) -> MagicMock:
    project = MagicMock()
    project.id = project_id
    project.name = "Test Project"
    project.description = "Test"
    project.status = "active"
    project.client_org_id = 1
    project.created_by_id = 1
    project.is_active = True
    project.deleted_at = None
    project.target_clients = None
    project.qa_profile = None
    project.design_system = None
    project.created_at = "2026-01-01T00:00:00Z"
    project.updated_at = "2026-01-01T00:00:00Z"
    return project


def _make_non_member(user_id: int = 99) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.role = "developer"
    return user


def _make_admin(user_id: int = 1) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.role = "admin"
    return user


async def test_update_project_denied_for_non_member(service):
    """Non-member developer cannot update a project."""
    service.projects.get = AsyncMock(return_value=_make_project())
    service.projects.get_member = AsyncMock(return_value=None)

    with pytest.raises(ProjectAccessDeniedError):
        await service.update_project(1, ProjectUpdate(name="hack"), _make_non_member())


async def test_delete_project_denied_for_non_member(service):
    """Non-member developer cannot delete a project."""
    service.projects.get = AsyncMock(return_value=_make_project())
    service.projects.get_member = AsyncMock(return_value=None)

    with pytest.raises(ProjectAccessDeniedError):
        await service.delete_project(1, _make_non_member())


async def test_update_project_allowed_for_admin(service):
    """Admin users bypass project membership check."""
    project = _make_project()
    service.projects.get = AsyncMock(return_value=project)
    service.projects.update = AsyncMock(return_value=project)

    result = await service.update_project(1, ProjectUpdate(name="ok"), _make_admin())
    assert result is not None


async def test_delete_project_allowed_for_admin(service):
    """Admin users can delete any project."""
    project = _make_project()
    service.projects.get = AsyncMock(return_value=project)
    service.projects.delete = AsyncMock()

    await service.delete_project(1, _make_admin())
    service.projects.delete.assert_awaited_once()
