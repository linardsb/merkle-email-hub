"""Tests for auto-save blueprint output as TemplateVersion."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.blueprints.engine import BlueprintRun
from app.ai.blueprints.schemas import BlueprintRunRequest
from app.ai.blueprints.service import BlueprintService


def _make_run(
    *, status: str = "completed", html: str = "<html>ok</html>", brief: str = "Test brief"
) -> BlueprintRun:
    run = BlueprintRun(html=html, brief_text=brief)
    run.status = status
    return run


def _make_request(*, template_id: int | None = None) -> BlueprintRunRequest:
    return BlueprintRunRequest(
        blueprint_name="campaign",
        brief="Build a promo email",
        template_id=template_id,
    )


class TestAutoSaveTemplateVersion:
    """Tests for BlueprintService._auto_save_template_version."""

    @pytest.mark.asyncio()
    async def test_successful_run_saves_version_to_existing_template(self) -> None:
        service = BlueprintService()
        bp_run = _make_run()
        request = _make_request(template_id=42)
        db = AsyncMock()

        mock_version = MagicMock()
        mock_version.id = 99

        with patch("app.templates.repository.TemplateRepository") as MockRepo:
            MockRepo.return_value.create_version = AsyncMock(return_value=mock_version)
            result = await service._auto_save_template_version(
                bp_run, request, project_id=1, user_id=10, db=db
            )

        assert result == 99
        MockRepo.return_value.create_version.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_successful_run_creates_new_template_when_no_template_id(self) -> None:
        service = BlueprintService()
        bp_run = _make_run()
        request = _make_request(template_id=None)
        db = AsyncMock()

        mock_template = MagicMock()
        mock_template.id = 7

        mock_version = MagicMock()
        mock_version.id = 77

        with patch("app.templates.repository.TemplateRepository") as MockRepo:
            MockRepo.return_value.create = AsyncMock(return_value=mock_template)
            MockRepo.return_value.get_versions = AsyncMock(return_value=[mock_version])
            result = await service._auto_save_template_version(
                bp_run, request, project_id=1, user_id=10, db=db
            )

        assert result == 77
        MockRepo.return_value.create.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_failed_run_does_not_save(self) -> None:
        service = BlueprintService()
        bp_run = _make_run(status="failed")
        request = _make_request(template_id=42)
        db = AsyncMock()

        result = await service._auto_save_template_version(
            bp_run, request, project_id=1, user_id=10, db=db
        )
        assert result is None

    @pytest.mark.asyncio()
    async def test_auto_save_failure_does_not_crash_response(self) -> None:
        service = BlueprintService()
        bp_run = _make_run()
        request = _make_request(template_id=42)
        db = AsyncMock()

        with patch("app.templates.repository.TemplateRepository") as MockRepo:
            MockRepo.return_value.create_version = AsyncMock(side_effect=RuntimeError("DB down"))
            result = await service._auto_save_template_version(
                bp_run, request, project_id=1, user_id=10, db=db
            )

        assert result is None

    @pytest.mark.asyncio()
    async def test_no_save_without_db(self) -> None:
        service = BlueprintService()
        bp_run = _make_run()
        request = _make_request(template_id=42)

        result = await service._auto_save_template_version(
            bp_run, request, project_id=1, user_id=10, db=None
        )
        assert result is None

    @pytest.mark.asyncio()
    async def test_no_save_without_user_id(self) -> None:
        service = BlueprintService()
        bp_run = _make_run()
        request = _make_request(template_id=42)
        db = AsyncMock()

        result = await service._auto_save_template_version(
            bp_run, request, project_id=1, user_id=None, db=db
        )
        assert result is None

    @pytest.mark.asyncio()
    async def test_no_save_without_project_id_and_no_template_id(self) -> None:
        service = BlueprintService()
        bp_run = _make_run()
        request = _make_request(template_id=None)
        db = AsyncMock()

        result = await service._auto_save_template_version(
            bp_run, request, project_id=None, user_id=10, db=db
        )
        assert result is None


class TestBriefTextInResponse:
    """Tests that brief_text flows through to response."""

    def test_brief_text_on_blueprint_run(self) -> None:
        run = BlueprintRun(html="<html></html>", brief_text="My brief")
        assert run.brief_text == "My brief"

    def test_brief_text_default_empty(self) -> None:
        run = BlueprintRun()
        assert run.brief_text == ""
