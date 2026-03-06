# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""BOLA authorization tests for QA engine override endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.projects.exceptions import ProjectAccessDeniedError
from app.projects.service import ProjectService
from app.qa_engine.schemas import QAOverrideRequest
from app.qa_engine.service import QAEngineService
from app.qa_engine.tests.conftest import make_qa_check, make_qa_result


@pytest.fixture
def service() -> QAEngineService:
    mock_db = AsyncMock()
    svc = QAEngineService(mock_db)
    svc.repository = AsyncMock()
    return svc


def _make_non_member(user_id: int = 99) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.role = "developer"
    return user


async def test_override_denied_for_non_member(service):
    """Non-member cannot override QA results for a build they don't have access to."""
    checks = [make_qa_check(id=1, check_name="dark_mode", passed=False, score=0.3)]
    qa_result = make_qa_result(id=10, build_id=42, passed=False)
    qa_result.checks = checks
    qa_result.override = None

    service.repository.get_result_with_checks = AsyncMock(return_value=qa_result)

    # Mock the build lookup to return a project_id
    mock_build_result = MagicMock()
    mock_build_result.scalar_one_or_none.return_value = 1  # project_id = 1
    service.db.execute = AsyncMock(return_value=mock_build_result)

    with patch.object(
        ProjectService, "verify_project_access", side_effect=ProjectAccessDeniedError("denied")
    ):
        with pytest.raises(ProjectAccessDeniedError):
            data = QAOverrideRequest(
                justification="Approved after manual review", checks_overridden=["dark_mode"]
            )
            await service.override_result(10, data, _make_non_member())


async def test_override_allowed_when_no_project_link(service):
    """Override proceeds when QA result has no build_id or template_version_id."""
    checks = [make_qa_check(id=1, check_name="dark_mode", passed=False, score=0.3)]
    qa_result = make_qa_result(id=10, build_id=None, template_version_id=None, passed=False)
    qa_result.checks = checks
    qa_result.override = None

    override = MagicMock()
    override.id = 1
    override.qa_result_id = 10
    override.overridden_by_id = 99
    override.justification = "test"
    override.checks_overridden = ["dark_mode"]

    service.repository.get_result_with_checks = AsyncMock(return_value=qa_result)
    service.repository.get_override_by_result_id = AsyncMock(return_value=None)
    service.repository.create_override = AsyncMock(return_value=override)

    data = QAOverrideRequest(
        justification="Approved after manual review", checks_overridden=["dark_mode"]
    )
    result = await service.override_result(10, data, _make_non_member())
    assert result.qa_result_id == 10
