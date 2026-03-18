# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Unit tests for QAEngineService business logic."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.qa_engine.exceptions import QAOverrideNotAllowedError, QAResultNotFoundError
from app.qa_engine.schemas import QAOverrideRequest, QARunRequest
from app.qa_engine.service import QAEngineService
from app.qa_engine.tests.conftest import make_qa_check, make_qa_override, make_qa_result
from app.shared.schemas import PaginationParams


@pytest.fixture
def service() -> QAEngineService:
    mock_db = AsyncMock()
    svc = QAEngineService(mock_db)
    svc.repository = AsyncMock()
    return svc


@pytest.fixture
def mock_user() -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.role = "developer"
    return user


# ── Run Checks ──


async def test_run_checks_returns_13_results(service):
    """Running QA should execute all 13 checks and persist results."""
    data = QARunRequest(html="<!DOCTYPE html><html><body>Hello</body></html>")

    qa_result = make_qa_result(id=1)
    service.repository.create_result = AsyncMock(return_value=qa_result)
    service.repository.create_checks = AsyncMock()

    result = await service.run_checks(data)

    assert result.checks_total == 13
    assert len(result.checks) == 13
    assert result.id == 1
    service.repository.create_result.assert_awaited_once()
    service.repository.create_checks.assert_awaited_once()


async def test_run_checks_with_build_id(service):
    data = QARunRequest(build_id=42, html="<!DOCTYPE html><html><body>Test</body></html>")
    qa_result = make_qa_result(id=2, build_id=42)
    service.repository.create_result = AsyncMock(return_value=qa_result)
    service.repository.create_checks = AsyncMock()

    result = await service.run_checks(data)

    assert result.build_id == 42
    call_kwargs = service.repository.create_result.call_args.kwargs
    assert call_kwargs["build_id"] == 42


async def test_run_checks_with_template_version_id(service):
    data = QARunRequest(
        template_version_id=99, html="<!DOCTYPE html><html><body>Test</body></html>"
    )
    qa_result = make_qa_result(id=3, template_version_id=99)
    service.repository.create_result = AsyncMock(return_value=qa_result)
    service.repository.create_checks = AsyncMock()

    result = await service.run_checks(data)

    assert result.template_version_id == 99


# ── Get Result ──


async def test_get_result_success(service):
    checks = [
        make_qa_check(id=1, check_name="html_validation", passed=True, score=1.0),
        make_qa_check(id=2, check_name="css_support", passed=True, score=1.0),
    ]
    qa_result = make_qa_result(id=10, checks_passed=2, checks_total=2)
    qa_result.checks = checks
    qa_result.override = None
    service.repository.get_result_with_checks = AsyncMock(return_value=qa_result)

    result = await service.get_result(10)

    assert result.id == 10
    assert len(result.checks) == 2
    assert result.override is None


async def test_get_result_with_override(service):
    checks = [make_qa_check(id=1, check_name="dark_mode", passed=False, score=0.5)]
    override = make_qa_override(qa_result_id=10, checks_overridden=["dark_mode"])
    qa_result = make_qa_result(id=10, passed=False)
    qa_result.checks = checks
    qa_result.override = override
    service.repository.get_result_with_checks = AsyncMock(return_value=qa_result)

    result = await service.get_result(10)

    assert result.override is not None
    assert result.override.checks_overridden == ["dark_mode"]


async def test_get_result_not_found(service):
    service.repository.get_result_with_checks = AsyncMock(return_value=None)

    with pytest.raises(QAResultNotFoundError, match="QA result 999 not found"):
        await service.get_result(999)


# ── List Results ──


async def test_list_results_returns_paginated(service):
    items = [make_qa_result(id=1), make_qa_result(id=2)]
    for item in items:
        item.checks = []
        item.override = None
    service.repository.list_results = AsyncMock(return_value=items)
    service.repository.count_results = AsyncMock(return_value=2)

    pagination = PaginationParams(page=1, page_size=20)
    result = await service.list_results(pagination)

    assert len(result.items) == 2
    assert result.total == 2
    assert result.page == 1


async def test_list_results_with_filters(service):
    items = [make_qa_result(id=1, passed=True)]
    for item in items:
        item.checks = []
        item.override = None
    service.repository.list_results = AsyncMock(return_value=items)
    service.repository.count_results = AsyncMock(return_value=1)

    pagination = PaginationParams(page=1, page_size=10)
    result = await service.list_results(pagination, passed=True, build_id=42)

    assert len(result.items) == 1
    service.repository.list_results.assert_awaited_once_with(
        build_id=42,
        template_version_id=None,
        passed=True,
        offset=0,
        limit=10,
    )


# ── Get Latest Result ──


async def test_get_latest_result_success(service):
    qa_result = make_qa_result(id=5)
    qa_result.checks = []
    qa_result.override = None
    service.repository.get_latest_result = AsyncMock(return_value=qa_result)

    result = await service.get_latest_result(build_id=42)

    assert result.id == 5
    service.repository.get_latest_result.assert_awaited_once_with(
        build_id=42,
        template_version_id=None,
    )


async def test_get_latest_result_not_found(service):
    service.repository.get_latest_result = AsyncMock(return_value=None)

    with pytest.raises(QAResultNotFoundError, match="No QA results found"):
        await service.get_latest_result(build_id=999)


# ── Override Result ──


async def test_override_failing_result(service, mock_user):
    checks = [
        make_qa_check(id=1, check_name="dark_mode", passed=False, score=0.3),
        make_qa_check(id=2, check_name="fallback", passed=False, score=0.2),
        make_qa_check(id=3, check_name="html_validation", passed=True, score=1.0),
    ]
    qa_result = make_qa_result(id=10, passed=False)
    qa_result.checks = checks
    qa_result.override = None

    override = make_qa_override(
        qa_result_id=10,
        overridden_by_id=1,
        checks_overridden=["dark_mode", "fallback"],
    )

    service.repository.get_result_with_checks = AsyncMock(return_value=qa_result)
    service.repository.get_override_by_result_id = AsyncMock(return_value=None)
    service.repository.create_override = AsyncMock(return_value=override)

    data = QAOverrideRequest(
        justification="Approved after manual review of dark mode rendering.",
        checks_overridden=["dark_mode", "fallback"],
    )
    result = await service.override_result(10, data, mock_user)

    assert result.checks_overridden == ["dark_mode", "fallback"]
    assert result.qa_result_id == 10
    service.repository.create_override.assert_awaited_once()


async def test_override_passing_result_raises(service, mock_user):
    qa_result = make_qa_result(id=10, passed=True)
    qa_result.checks = []
    qa_result.override = None
    service.repository.get_result_with_checks = AsyncMock(return_value=qa_result)

    data = QAOverrideRequest(
        justification="This should not be allowed.",
        checks_overridden=["html_validation"],
    )
    with pytest.raises(QAOverrideNotAllowedError, match="Cannot override a passing"):
        await service.override_result(10, data, mock_user)


async def test_override_invalid_check_name_raises(service, mock_user):
    checks = [
        make_qa_check(id=1, check_name="dark_mode", passed=False, score=0.3),
        make_qa_check(id=2, check_name="html_validation", passed=True, score=1.0),
    ]
    qa_result = make_qa_result(id=10, passed=False)
    qa_result.checks = checks
    qa_result.override = None
    service.repository.get_result_with_checks = AsyncMock(return_value=qa_result)

    data = QAOverrideRequest(
        justification="Trying to override a check that passed.",
        checks_overridden=["html_validation"],  # This check passed!
    )
    with pytest.raises(QAOverrideNotAllowedError, match="html_validation"):
        await service.override_result(10, data, mock_user)


async def test_override_nonexistent_check_raises(service, mock_user):
    checks = [make_qa_check(id=1, check_name="dark_mode", passed=False, score=0.3)]
    qa_result = make_qa_result(id=10, passed=False)
    qa_result.checks = checks
    qa_result.override = None
    service.repository.get_result_with_checks = AsyncMock(return_value=qa_result)

    data = QAOverrideRequest(
        justification="Overriding a check that doesn't exist.",
        checks_overridden=["nonexistent_check"],
    )
    with pytest.raises(QAOverrideNotAllowedError, match="nonexistent_check"):
        await service.override_result(10, data, mock_user)


async def test_override_replaces_existing(service, mock_user):
    """If an override already exists, it should be replaced."""
    checks = [make_qa_check(id=1, check_name="dark_mode", passed=False, score=0.3)]
    qa_result = make_qa_result(id=10, passed=False)
    qa_result.checks = checks
    qa_result.override = None

    existing_override = make_qa_override(qa_result_id=10)
    new_override = make_qa_override(
        id=2,
        qa_result_id=10,
        justification="Updated justification.",
    )

    service.repository.get_result_with_checks = AsyncMock(return_value=qa_result)
    service.repository.get_override_by_result_id = AsyncMock(return_value=existing_override)
    service.repository.create_override = AsyncMock(return_value=new_override)

    data = QAOverrideRequest(
        justification="Updated justification for override.",
        checks_overridden=["dark_mode"],
    )
    result = await service.override_result(10, data, mock_user)

    assert result.id == 2
    # Verify the old override was deleted
    service.db.delete.assert_awaited_once_with(existing_override)


async def test_override_result_not_found(service, mock_user):
    service.repository.get_result_with_checks = AsyncMock(return_value=None)

    data = QAOverrideRequest(
        justification="This result doesn't exist.",
        checks_overridden=["dark_mode"],
    )
    with pytest.raises(QAResultNotFoundError, match="QA result 999"):
        await service.override_result(999, data, mock_user)
