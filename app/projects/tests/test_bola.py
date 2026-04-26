# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false, reportFunctionMemberAccess=false, reportUnusedFunction=false
"""BOLA authorization tests for project endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ForbiddenError
from app.core.rate_limit import limiter
from app.core.scoped_db import TenantAccess
from app.projects.exceptions import ProjectAccessDeniedError
from app.projects.routes import list_projects
from app.projects.schemas import ProjectUpdate
from app.projects.service import ProjectService
from app.shared.schemas import PaginationParams


@pytest.fixture
def _disable_limiter():
    """Disable slowapi rate limiter so route handlers can be called directly."""
    prev = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = prev


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
    project.template_config = None
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


# ── F003: list_projects?client_org_id= cross-tenant guard ──


def _service_with_access(access: TenantAccess) -> tuple[ProjectService, AsyncMock]:
    """Build a ProjectService whose db.session.info carries tenant_access.

    Returns the service plus the `list_projects` AsyncMock so callers can
    assert call counts without tripping pyright on a method-assigned mock.
    """
    mock_db = MagicMock()
    mock_db.info = {"tenant_access": access}
    svc = ProjectService(mock_db)
    list_mock = AsyncMock(return_value=MagicMock())
    svc.list_projects = list_mock  # type: ignore[method-assign]
    return svc, list_mock


@pytest.mark.tenant_isolation
async def test_list_projects_rejects_unauthorized_client_org_id_for_non_admin(_disable_limiter):
    """F003: non-admin asking for client_org_id outside their orgs is rejected."""
    access = TenantAccess(project_ids=frozenset({1}), org_ids=frozenset({10}), role="developer")
    svc, list_mock = _service_with_access(access)
    user = _make_non_member()

    with pytest.raises(ForbiddenError, match="does not have access to client org 99"):
        await list_projects(
            request=MagicMock(),
            pagination=PaginationParams(),
            client_org_id=99,
            search=None,
            service=svc,
            current_user=user,
        )
    list_mock.assert_not_awaited()


@pytest.mark.tenant_isolation
async def test_list_projects_allows_authorized_client_org_id_for_non_admin(_disable_limiter):
    """Non-admin asking for an org they belong to passes through."""
    access = TenantAccess(project_ids=frozenset({1}), org_ids=frozenset({10}), role="developer")
    svc, list_mock = _service_with_access(access)
    user = _make_non_member()

    await list_projects(
        request=MagicMock(),
        pagination=PaginationParams(),
        client_org_id=10,
        search=None,
        service=svc,
        current_user=user,
    )
    list_mock.assert_awaited_once()


@pytest.mark.tenant_isolation
async def test_list_projects_admin_bypasses_client_org_check(_disable_limiter):
    """Admin requesting any client_org_id skips the membership check (sentinel = None)."""
    access = TenantAccess(project_ids=None, org_ids=None, role="admin")
    svc, list_mock = _service_with_access(access)
    user = _make_admin()

    await list_projects(
        request=MagicMock(),
        pagination=PaginationParams(),
        client_org_id=999,
        search=None,
        service=svc,
        current_user=user,
    )
    list_mock.assert_awaited_once()


@pytest.mark.tenant_isolation
async def test_list_projects_no_client_org_id_skips_check(_disable_limiter):
    """No client_org_id filter → no membership check fires."""
    access = TenantAccess(project_ids=frozenset({1}), org_ids=frozenset({10}), role="developer")
    svc, list_mock = _service_with_access(access)
    user = _make_non_member()

    await list_projects(
        request=MagicMock(),
        pagination=PaginationParams(),
        client_org_id=None,
        search=None,
        service=svc,
        current_user=user,
    )
    list_mock.assert_awaited_once()
