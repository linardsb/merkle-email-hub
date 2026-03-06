# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""BOLA authorization tests for rendering compare endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.projects.exceptions import ProjectAccessDeniedError
from app.projects.service import ProjectService
from app.rendering.schemas import RenderingComparisonRequest
from app.rendering.service import RenderingService


@pytest.fixture
def service() -> RenderingService:
    mock_db = AsyncMock()
    svc = RenderingService(mock_db)
    svc.repository = AsyncMock()
    return svc


def _make_non_member(user_id: int = 99) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.role = "developer"
    return user


def _make_test(test_id: int = 1, build_id: int | None = 42) -> MagicMock:
    test = MagicMock()
    test.id = test_id
    test.build_id = build_id
    test.screenshots = []
    return test


async def test_compare_denied_for_non_member(service):
    """Non-member cannot compare rendering tests from a project they don't belong to."""
    baseline = _make_test(test_id=1)
    current = _make_test(test_id=2)
    service.repository.get_test = AsyncMock(side_effect=[baseline, current])

    # Mock the build lookup to return a project_id
    mock_build_result = MagicMock()
    mock_build_result.scalar_one_or_none.return_value = 1  # project_id
    service.db.execute = AsyncMock(return_value=mock_build_result)

    with patch.object(
        ProjectService, "verify_project_access", side_effect=ProjectAccessDeniedError("denied")
    ):
        with pytest.raises(ProjectAccessDeniedError):
            data = RenderingComparisonRequest(baseline_test_id=1, current_test_id=2)
            await service.compare_tests(data, _make_non_member())


async def test_compare_allowed_when_no_build_link(service):
    """Compare proceeds when tests have no build_id."""
    baseline = _make_test(test_id=1, build_id=None)
    current = _make_test(test_id=2, build_id=None)
    baseline.screenshots = []
    current.screenshots = []
    service.repository.get_test = AsyncMock(side_effect=[baseline, current])

    data = RenderingComparisonRequest(baseline_test_id=1, current_test_id=2)
    result = await service.compare_tests(data, _make_non_member())
    assert result.total_clients == 0
