# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Service-layer tests for chaos engine and property testing."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import DomainValidationError, ForbiddenError
from app.qa_engine.schemas import (
    ChaosFailure,
    ChaosTestRequest,
    ChaosTestResponse,
    PropertyTestRequest,
    PropertyTestResponse,
)
from app.qa_engine.service import QAEngineService


def _make_service() -> QAEngineService:
    db = AsyncMock()
    return QAEngineService(db)


def _make_user(role: str = "developer") -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.role = role
    return user


def _chaos_settings(
    *,
    enabled: bool = True,
    auto_document: bool = False,
    resilience_check_enabled: bool = False,
    resilience_threshold: float = 0.7,
) -> MagicMock:
    settings = MagicMock()
    settings.qa_chaos.enabled = enabled
    settings.qa_chaos.auto_document = auto_document
    settings.qa_chaos.default_profiles = ["gmail_style_strip"]
    settings.qa_chaos.resilience_check_enabled = resilience_check_enabled
    settings.qa_chaos.resilience_threshold = resilience_threshold
    settings.qa_property_testing.enabled = True
    settings.qa_property_testing.seed = 42
    settings.qa_property_testing.default_cases = 10
    return settings


def _mock_chaos_response(
    *, critical_failures: list[ChaosFailure] | None = None
) -> ChaosTestResponse:
    return ChaosTestResponse(
        original_score=0.8,
        resilience_score=0.7,
        profiles_tested=2,
        profile_results=[],
        critical_failures=critical_failures or [],
    )


MINIMAL_HTML = "<!DOCTYPE html><html><head></head><body><p>Hello</p></body></html>"


class TestRunChaosTest:
    @pytest.mark.asyncio
    async def test_disabled_raises_forbidden(self) -> None:
        service = _make_service()
        data = ChaosTestRequest(html=MINIMAL_HTML)
        with patch("app.qa_engine.service.get_settings") as mock_gs:
            mock_gs.return_value.qa_chaos.enabled = False
            with pytest.raises(ForbiddenError, match="not enabled"):
                await service.run_chaos_test(data)

    @pytest.mark.asyncio
    async def test_returns_response(self) -> None:
        service = _make_service()
        data = ChaosTestRequest(html=MINIMAL_HTML)
        mock_resp = _mock_chaos_response()
        with (
            patch("app.qa_engine.service.get_settings", return_value=_chaos_settings()),
            patch(
                "app.qa_engine.chaos.engine.ChaosEngine.run_chaos_test",
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            result = await service.run_chaos_test(data)
        assert result.resilience_score == 0.7
        assert result.profiles_tested == 2

    @pytest.mark.asyncio
    async def test_auto_document_on_critical_failures(self) -> None:
        service = _make_service()
        user = _make_user()
        failures = [
            ChaosFailure(
                profile="gmail_style_strip",
                check_name="css_support",
                severity="error",
                description="CSS failed",
            )
        ]
        data = ChaosTestRequest(html=MINIMAL_HTML, project_id=5)
        mock_resp = _mock_chaos_response(critical_failures=failures)
        settings = _chaos_settings(auto_document=True)
        with (
            patch("app.qa_engine.service.get_settings", return_value=settings),
            patch(
                "app.qa_engine.chaos.engine.ChaosEngine.run_chaos_test",
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
            patch(
                "app.qa_engine.service.ProjectService.verify_project_access",
                new_callable=AsyncMock,
            ),
            patch(
                "app.qa_engine.chaos.knowledge_writer.ChaosKnowledgeWriter.write_failure_documents",
                new_callable=AsyncMock,
                return_value=[10],
            ) as mock_writer,
        ):
            result = await service.run_chaos_test(data, user=user)
        assert result.resilience_score == 0.7
        mock_writer.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_document_skipped_no_project_id(self) -> None:
        service = _make_service()
        user = _make_user()
        failures = [
            ChaosFailure(
                profile="gmail_style_strip",
                check_name="css_support",
                severity="error",
                description="CSS failed",
            )
        ]
        data = ChaosTestRequest(html=MINIMAL_HTML)  # no project_id
        mock_resp = _mock_chaos_response(critical_failures=failures)
        settings = _chaos_settings(auto_document=True)
        with (
            patch("app.qa_engine.service.get_settings", return_value=settings),
            patch(
                "app.qa_engine.chaos.engine.ChaosEngine.run_chaos_test",
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
            patch(
                "app.qa_engine.chaos.knowledge_writer.ChaosKnowledgeWriter.write_failure_documents",
                new_callable=AsyncMock,
            ) as mock_writer,
        ):
            result = await service.run_chaos_test(data, user=user)
        assert result.resilience_score == 0.7
        mock_writer.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_document_skipped_no_user(self) -> None:
        service = _make_service()
        failures = [
            ChaosFailure(
                profile="gmail_style_strip",
                check_name="css_support",
                severity="error",
                description="CSS failed",
            )
        ]
        data = ChaosTestRequest(html=MINIMAL_HTML, project_id=5)
        mock_resp = _mock_chaos_response(critical_failures=failures)
        settings = _chaos_settings(auto_document=True)
        with (
            patch("app.qa_engine.service.get_settings", return_value=settings),
            patch(
                "app.qa_engine.chaos.engine.ChaosEngine.run_chaos_test",
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
            patch(
                "app.qa_engine.chaos.knowledge_writer.ChaosKnowledgeWriter.write_failure_documents",
                new_callable=AsyncMock,
            ) as mock_writer,
        ):
            result = await service.run_chaos_test(data, user=None)
        assert result.resilience_score == 0.7
        mock_writer.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_document_failure_non_blocking(self) -> None:
        service = _make_service()
        user = _make_user()
        failures = [
            ChaosFailure(
                profile="gmail_style_strip",
                check_name="css_support",
                severity="error",
                description="CSS failed",
            )
        ]
        data = ChaosTestRequest(html=MINIMAL_HTML, project_id=5)
        mock_resp = _mock_chaos_response(critical_failures=failures)
        settings = _chaos_settings(auto_document=True)
        with (
            patch("app.qa_engine.service.get_settings", return_value=settings),
            patch(
                "app.qa_engine.chaos.engine.ChaosEngine.run_chaos_test",
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
            patch(
                "app.qa_engine.service.ProjectService.verify_project_access",
                new_callable=AsyncMock,
            ),
            patch(
                "app.qa_engine.chaos.knowledge_writer.ChaosKnowledgeWriter.write_failure_documents",
                new_callable=AsyncMock,
                side_effect=RuntimeError("DB error"),
            ),
        ):
            # Should NOT raise despite writer failure
            result = await service.run_chaos_test(data, user=user)
        assert result.resilience_score == 0.7


class TestRunPropertyTest:
    @pytest.mark.asyncio
    async def test_disabled_raises_forbidden(self) -> None:
        service = _make_service()
        data = PropertyTestRequest(num_cases=5)
        with patch("app.qa_engine.service.get_settings") as mock_gs:
            mock_gs.return_value.qa_property_testing.enabled = False
            with pytest.raises(ForbiddenError, match="not enabled"):
                await service.run_property_test(data)

    @pytest.mark.asyncio
    async def test_returns_response(self) -> None:
        service = _make_service()
        data = PropertyTestRequest(num_cases=5, seed=42)
        settings = _chaos_settings()
        with patch("app.qa_engine.service.get_settings", return_value=settings):
            result = await service.run_property_test(data)
        assert isinstance(result, PropertyTestResponse)
        assert result.total_cases == 5
        assert result.seed == 42

    @pytest.mark.asyncio
    async def test_config_fallback_seed(self) -> None:
        """When no seed in request, config default is used."""
        service = _make_service()
        data = PropertyTestRequest(num_cases=3)  # no seed
        settings = _chaos_settings()
        settings.qa_property_testing.seed = 999
        with patch("app.qa_engine.service.get_settings", return_value=settings):
            result = await service.run_property_test(data)
        assert result.seed == 999

    @pytest.mark.asyncio
    async def test_config_fallback_num_cases(self) -> None:
        """When no num_cases in request, config default is used."""
        service = _make_service()
        data = PropertyTestRequest(seed=42)  # no num_cases
        settings = _chaos_settings()
        settings.qa_property_testing.default_cases = 7
        with patch("app.qa_engine.service.get_settings", return_value=settings):
            result = await service.run_property_test(data)
        assert result.total_cases == 7

    @pytest.mark.asyncio
    async def test_unknown_invariant_propagates(self) -> None:
        service = _make_service()
        data = PropertyTestRequest(invariants=["bogus_invariant"], num_cases=5, seed=1)
        settings = _chaos_settings()
        with (
            patch("app.qa_engine.service.get_settings", return_value=settings),
            pytest.raises(DomainValidationError, match="Unknown invariants"),
        ):
            await service.run_property_test(data)
