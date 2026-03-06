# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""BOLA authorization tests for connector export endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.connectors.schemas import ExportRequest
from app.connectors.service import ConnectorService
from app.projects.exceptions import ProjectAccessDeniedError
from app.projects.service import ProjectService


@pytest.fixture
def service() -> ConnectorService:
    mock_db = AsyncMock()
    svc = ConnectorService(mock_db)
    return svc


def _make_non_member(user_id: int = 99) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.role = "developer"
    return user


def _make_build(project_id: int = 1) -> MagicMock:
    build = MagicMock()
    build.id = 42
    build.project_id = project_id
    return build


async def test_export_denied_for_non_member(service):
    """Non-member cannot export a build from a project they don't belong to."""
    build = _make_build()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = build
    service.db.execute = AsyncMock(return_value=mock_result)

    with patch.object(
        ProjectService, "verify_project_access", side_effect=ProjectAccessDeniedError("denied")
    ):
        with pytest.raises(ProjectAccessDeniedError):
            data = ExportRequest(build_id=42, connector_type="braze", content_block_name="Test")
            await service.export(data, _make_non_member())


async def test_export_build_not_found(service):
    """Export fails with NotFoundError when build doesn't exist."""
    from app.core.exceptions import NotFoundError

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    service.db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(NotFoundError, match="Build 999"):
        data = ExportRequest(build_id=999, connector_type="braze", content_block_name="Test")
        await service.export(data, _make_non_member())
