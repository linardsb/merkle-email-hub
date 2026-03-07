"""Tests for email build BOLA authorization."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ForbiddenError
from app.email_engine.service import EmailEngineService


def _make_user(user_id: int = 1, role: str = "developer") -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.role = role
    return user


def _make_build(build_id: int = 1, project_id: int = 10) -> MagicMock:
    build = MagicMock()
    build.id = build_id
    build.project_id = project_id
    build.template_name = "test-template"
    build.status = "success"
    build.compiled_html = "<html></html>"
    build.error_message = None
    build.is_production = False
    build.created_at = "2026-01-01T00:00:00"
    return build


class TestGetBuildAuthorization:
    """Verify get_build enforces project access."""

    @pytest.mark.asyncio
    async def test_non_member_gets_forbidden(self) -> None:
        """User without project access should get ForbiddenError."""
        build = _make_build(build_id=5, project_id=10)
        user = _make_user(user_id=99)

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = build
        db.execute.return_value = result_mock

        service = EmailEngineService(db)

        with patch(
            "app.projects.service.ProjectService.verify_project_access",
            new_callable=AsyncMock,
            side_effect=ForbiddenError("Access denied"),
        ) as mock_verify:
            with pytest.raises(ForbiddenError):
                await service.get_build(5, user)

            mock_verify.assert_called_once_with(10, user)

    @pytest.mark.asyncio
    async def test_project_member_succeeds(self) -> None:
        """User with project access should get the build."""
        build = _make_build(build_id=5, project_id=10)
        user = _make_user(user_id=1)

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = build
        db.execute.return_value = result_mock

        service = EmailEngineService(db)

        with patch(
            "app.projects.service.ProjectService.verify_project_access",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ) as mock_verify:
            result = await service.get_build(5, user)
            assert result is not None
            mock_verify.assert_called_once_with(10, user)

    @pytest.mark.asyncio
    async def test_build_not_found(self) -> None:
        """Non-existent build should raise before authorization check."""
        from app.email_engine.exceptions import BuildFailedError

        user = _make_user()

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        service = EmailEngineService(db)

        with pytest.raises(BuildFailedError, match="not found"):
            await service.get_build(999, user)
