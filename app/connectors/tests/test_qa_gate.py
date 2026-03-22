"""Unit tests for the export QA gate (Phase 28.1)."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.connectors.exceptions import ExportQAGateBlockedError
from app.connectors.qa_gate import ExportQAGate
from app.connectors.qa_gate_schemas import (
    ExportQAConfig,
    QAGateMode,
    QAGateResult,
    QAGateVerdict,
)
from app.qa_engine.schemas import QACheckResult, QAResultResponse


def _make_qa_response(
    checks: list[QACheckResult],
    passed: bool = True,
) -> QAResultResponse:
    """Build a minimal QAResultResponse for testing."""
    return QAResultResponse(
        id=1,
        build_id=None,
        template_version_id=None,
        overall_score=0.9 if passed else 0.3,
        passed=passed,
        checks_passed=sum(1 for c in checks if c.passed),
        checks_total=len(checks),
        checks=checks,
        created_at=datetime.datetime.now(datetime.UTC),
    )


def _check(name: str, passed: bool = True, score: float = 1.0) -> QACheckResult:
    return QACheckResult(check_name=name, passed=passed, score=score)


# ── ExportQAGate.evaluate() ──


class TestExportQAGateEvaluate:
    """Tests for ExportQAGate.evaluate()."""

    @pytest.fixture()
    def mock_db(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture()
    def gate(self, mock_db: AsyncMock) -> ExportQAGate:
        return ExportQAGate(mock_db)

    @pytest.mark.asyncio()
    async def test_all_checks_pass(self, gate: ExportQAGate) -> None:
        """All checks pass → PASS verdict."""
        checks = [_check("html_validation"), _check("link_validation"), _check("spam_score")]
        qa_resp = _make_qa_response(checks)

        with patch.object(
            gate, "_resolve_config", return_value=ExportQAConfig(mode=QAGateMode.enforce)
        ):
            with patch("app.qa_engine.service.QAEngineService") as mock_svc_cls:
                mock_svc_cls.return_value.run_checks = AsyncMock(return_value=qa_resp)
                result = await gate.evaluate("<html></html>")

        assert result.verdict == QAGateVerdict.PASS
        assert result.passed is True
        assert result.blocking_failures == []
        assert result.checks_run == 3

    @pytest.mark.asyncio()
    async def test_blocking_check_fails_enforce_mode(self, gate: ExportQAGate) -> None:
        """Blocking check fails in enforce mode → BLOCK verdict."""
        checks = [
            _check("html_validation", passed=False, score=0.2),
            _check("link_validation"),
        ]
        qa_resp = _make_qa_response(checks, passed=False)

        with patch.object(
            gate, "_resolve_config", return_value=ExportQAConfig(mode=QAGateMode.enforce)
        ):
            with patch("app.qa_engine.service.QAEngineService") as mock_svc_cls:
                mock_svc_cls.return_value.run_checks = AsyncMock(return_value=qa_resp)
                result = await gate.evaluate("<html></html>")

        assert result.verdict == QAGateVerdict.BLOCK
        assert result.passed is False
        assert len(result.blocking_failures) == 1
        assert result.blocking_failures[0].check_name == "html_validation"

    @pytest.mark.asyncio()
    async def test_blocking_check_fails_warn_mode(self, gate: ExportQAGate) -> None:
        """Blocking check fails in warn mode → WARN verdict, passed=True."""
        checks = [
            _check("html_validation", passed=False, score=0.2),
            _check("spam_score"),
        ]
        qa_resp = _make_qa_response(checks, passed=False)

        with patch.object(
            gate, "_resolve_config", return_value=ExportQAConfig(mode=QAGateMode.warn)
        ):
            with patch("app.qa_engine.service.QAEngineService") as mock_svc_cls:
                mock_svc_cls.return_value.run_checks = AsyncMock(return_value=qa_resp)
                result = await gate.evaluate("<html></html>")

        assert result.verdict == QAGateVerdict.WARN
        assert result.passed is True
        assert len(result.blocking_failures) == 1

    @pytest.mark.asyncio()
    async def test_warning_check_fails_does_not_block(self, gate: ExportQAGate) -> None:
        """Warning check failure → PASS verdict (warnings don't block)."""
        checks = [
            _check("html_validation"),
            _check("accessibility", passed=False, score=0.4),
        ]
        qa_resp = _make_qa_response(checks)

        with patch.object(
            gate, "_resolve_config", return_value=ExportQAConfig(mode=QAGateMode.enforce)
        ):
            with patch("app.qa_engine.service.QAEngineService") as mock_svc_cls:
                mock_svc_cls.return_value.run_checks = AsyncMock(return_value=qa_resp)
                result = await gate.evaluate("<html></html>")

        assert result.verdict == QAGateVerdict.PASS
        assert result.passed is True
        assert len(result.warnings) == 1
        assert result.warnings[0].check_name == "accessibility"

    @pytest.mark.asyncio()
    async def test_skip_mode_returns_pass_without_running_checks(self, gate: ExportQAGate) -> None:
        """Mode=skip → PASS without running QA checks."""
        with patch.object(
            gate, "_resolve_config", return_value=ExportQAConfig(mode=QAGateMode.skip)
        ):
            with patch("app.qa_engine.service.QAEngineService") as mock_svc_cls:
                result = await gate.evaluate("<html></html>")
                mock_svc_cls.return_value.run_checks.assert_not_called()

        assert result.verdict == QAGateVerdict.PASS
        assert result.passed is True
        assert result.checks_run == 0

    @pytest.mark.asyncio()
    async def test_ignored_check_not_counted(self, gate: ExportQAGate) -> None:
        """Ignored checks are excluded from verdict."""
        checks = [
            _check("html_validation", passed=False, score=0.1),
            _check("spam_score"),
        ]
        qa_resp = _make_qa_response(checks, passed=False)

        config = ExportQAConfig(mode=QAGateMode.enforce, ignored_checks=["html_validation"])
        with patch.object(gate, "_resolve_config", return_value=config):
            with patch("app.qa_engine.service.QAEngineService") as mock_svc_cls:
                mock_svc_cls.return_value.run_checks = AsyncMock(return_value=qa_resp)
                result = await gate.evaluate("<html></html>")

        assert result.verdict == QAGateVerdict.PASS
        assert result.passed is True
        assert result.blocking_failures == []

    @pytest.mark.asyncio()
    async def test_project_config_overrides_defaults(self, gate: ExportQAGate) -> None:
        """Per-project config loaded from DB overrides global defaults."""
        project_config = {
            "mode": "enforce",
            "blocking_checks": ["spam_score"],
            "warning_checks": [],
            "ignored_checks": ["html_validation"],
        }
        mock_project = MagicMock()
        mock_project.export_qa_config = project_config

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        gate.db.execute = AsyncMock(return_value=mock_result)  # type: ignore[method-assign]

        config = await gate._resolve_config(project_id=42)

        assert config.mode == QAGateMode.enforce
        assert config.blocking_checks == ["spam_score"]
        assert "html_validation" in config.ignored_checks


# ── ConnectorService.export() integration ──


class TestExportQAGateIntegration:
    """Tests for QA gate integration in ConnectorService.export()."""

    @pytest.fixture()
    def mock_db(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture()
    def mock_user_admin(self) -> MagicMock:
        user = MagicMock()
        user.id = 1
        user.role = "admin"
        return user

    @pytest.fixture()
    def mock_user_dev(self) -> MagicMock:
        user = MagicMock()
        user.id = 2
        user.role = "developer"
        return user

    @pytest.mark.asyncio()
    async def test_qa_gate_blocks_raises_error(
        self, mock_db: AsyncMock, mock_user_dev: MagicMock
    ) -> None:
        """QA gate BLOCK verdict raises ExportQAGateBlockedError."""
        from app.connectors.service import ConnectorService

        service = ConnectorService(mock_db)

        block_result = QAGateResult(
            passed=False,
            verdict=QAGateVerdict.BLOCK,
            mode=QAGateMode.enforce,
            blocking_failures=[],
            evaluated_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )

        with (
            patch.object(service, "_resolve_html", return_value="<html></html>"),
            patch.object(service, "_resolve_project_id", return_value=None),
            patch("app.connectors.service.get_settings") as mock_settings,
            patch("app.connectors.qa_gate.ExportQAGate") as mock_gate_cls,
        ):
            mock_settings.return_value.export.qa_gate_mode = "enforce"
            mock_settings.return_value.rendering.gate_mode = "skip"
            mock_gate_cls.return_value.evaluate = AsyncMock(return_value=block_result)

            from app.connectors.schemas import ExportRequest

            data = ExportRequest(build_id=1)

            with pytest.raises(ExportQAGateBlockedError):
                await service.export(data, mock_user_dev)

    @pytest.mark.asyncio()
    async def test_qa_gate_warns_proceeds(
        self, mock_db: AsyncMock, mock_user_dev: MagicMock
    ) -> None:
        """QA gate WARN verdict allows export, includes qa_gate_result."""
        from app.connectors.service import ConnectorService

        service = ConnectorService(mock_db)

        warn_result = QAGateResult(
            passed=True,
            verdict=QAGateVerdict.WARN,
            mode=QAGateMode.warn,
            blocking_failures=[],
            evaluated_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )

        with (
            patch.object(service, "_resolve_html", return_value="<html></html>"),
            patch.object(service, "_resolve_project_id", return_value=None),
            patch("app.connectors.service.get_settings") as mock_settings,
            patch("app.connectors.qa_gate.ExportQAGate") as mock_gate_cls,
        ):
            mock_settings.return_value.export.qa_gate_mode = "warn"
            mock_settings.return_value.rendering.gate_mode = "skip"
            mock_gate_cls.return_value.evaluate = AsyncMock(return_value=warn_result)

            from app.connectors.schemas import ExportRequest

            data = ExportRequest(template_version_id=1)

            resp = await service.export(data, mock_user_dev)
            assert resp.qa_gate_result is not None
            assert resp.qa_gate_result.verdict == QAGateVerdict.WARN

    @pytest.mark.asyncio()
    async def test_skip_qa_gate_admin_proceeds(
        self, mock_db: AsyncMock, mock_user_admin: MagicMock
    ) -> None:
        """Admin skip_qa_gate=True proceeds without QA checks."""
        from app.connectors.service import ConnectorService

        service = ConnectorService(mock_db)

        with (
            patch.object(service, "_resolve_html", return_value="<html></html>"),
            patch("app.connectors.service.get_settings") as mock_settings,
            patch("app.connectors.qa_gate.ExportQAGate") as mock_gate_cls,
        ):
            mock_settings.return_value.export.qa_gate_mode = "enforce"
            mock_settings.return_value.rendering.gate_mode = "skip"

            from app.connectors.schemas import ExportRequest

            data = ExportRequest(template_version_id=1, skip_qa_gate=True)

            resp = await service.export(data, mock_user_admin)
            mock_gate_cls.return_value.evaluate.assert_not_called()
            assert resp.qa_gate_result is None

    @pytest.mark.asyncio()
    async def test_skip_qa_gate_non_admin_forbidden(
        self, mock_db: AsyncMock, mock_user_dev: MagicMock
    ) -> None:
        """Non-admin skip_qa_gate=True raises ForbiddenError."""
        from app.connectors.service import ConnectorService
        from app.core.exceptions import ForbiddenError

        service = ConnectorService(mock_db)

        from app.connectors.schemas import ExportRequest

        data = ExportRequest(template_version_id=1, skip_qa_gate=True)

        with pytest.raises(ForbiddenError):
            await service.export(data, mock_user_dev)

    @pytest.mark.asyncio()
    async def test_qa_blocks_rendering_passes_still_blocked(
        self, mock_db: AsyncMock, mock_user_dev: MagicMock
    ) -> None:
        """QA gate blocks even if rendering gate would pass."""
        from app.connectors.service import ConnectorService

        service = ConnectorService(mock_db)

        block_result = QAGateResult(
            passed=False,
            verdict=QAGateVerdict.BLOCK,
            mode=QAGateMode.enforce,
            blocking_failures=[],
            evaluated_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )

        with (
            patch.object(service, "_resolve_html", return_value="<html></html>"),
            patch.object(service, "_resolve_project_id", return_value=None),
            patch("app.connectors.service.get_settings") as mock_settings,
            patch("app.connectors.qa_gate.ExportQAGate") as mock_gate_cls,
        ):
            mock_settings.return_value.export.qa_gate_mode = "enforce"
            # rendering gate would pass but QA should block first
            mock_settings.return_value.rendering.gate_mode = "warn"
            mock_gate_cls.return_value.evaluate = AsyncMock(return_value=block_result)

            from app.connectors.schemas import ExportRequest

            data = ExportRequest(build_id=1)

            with pytest.raises(ExportQAGateBlockedError):
                await service.export(data, mock_user_dev)

    @pytest.mark.asyncio()
    async def test_both_gates_pass_export_succeeds(
        self, mock_db: AsyncMock, mock_user_dev: MagicMock
    ) -> None:
        """Both QA and rendering gates pass → export succeeds."""
        from app.connectors.service import ConnectorService

        service = ConnectorService(mock_db)

        pass_result = QAGateResult(
            passed=True,
            verdict=QAGateVerdict.PASS,
            mode=QAGateMode.warn,
            evaluated_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )

        from app.rendering.gate_schemas import GateMode, GateResult, GateVerdict

        render_pass = GateResult(
            passed=True,
            verdict=GateVerdict.PASS,
            mode=GateMode.warn,
            evaluated_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )

        with (
            patch.object(service, "_resolve_html", return_value="<html></html>"),
            patch.object(service, "_resolve_project_id", return_value=None),
            patch("app.connectors.service.get_settings") as mock_settings,
            patch("app.connectors.qa_gate.ExportQAGate") as mock_gate_cls,
            patch("app.rendering.gate.RenderingSendGate") as mock_render_cls,
        ):
            mock_settings.return_value.export.qa_gate_mode = "warn"
            mock_settings.return_value.rendering.gate_mode = "warn"
            mock_gate_cls.return_value.evaluate = AsyncMock(return_value=pass_result)
            mock_render_cls.return_value.evaluate = AsyncMock(return_value=render_pass)

            from app.connectors.schemas import ExportRequest

            data = ExportRequest(template_version_id=1)

            resp = await service.export(data, mock_user_dev)
            assert resp.status == "success"
            assert resp.qa_gate_result is not None
            assert resp.qa_gate_result.passed is True


# ── Pre-check endpoint ──


class TestExportPreCheck:
    """Tests for ConnectorService.pre_check()."""

    @pytest.fixture()
    def mock_db(self) -> AsyncMock:
        return AsyncMock()

    @pytest.mark.asyncio()
    async def test_pre_check_returns_combined_results(self, mock_db: AsyncMock) -> None:
        """Pre-check returns combined QA + rendering results."""
        from app.connectors.qa_gate_schemas import ExportPreCheckRequest
        from app.connectors.service import ConnectorService

        service = ConnectorService(mock_db)

        qa_result = QAGateResult(
            passed=True,
            verdict=QAGateVerdict.PASS,
            mode=QAGateMode.warn,
            evaluated_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )

        with (
            patch("app.connectors.qa_gate.ExportQAGate") as mock_qa_cls,
            patch("app.connectors.service.get_settings") as mock_settings,
            patch("app.rendering.gate.RenderingSendGate") as mock_render_cls,
        ):
            mock_settings.return_value.rendering.gate_mode = "warn"
            mock_qa_cls.return_value.evaluate = AsyncMock(return_value=qa_result)

            from app.rendering.gate_schemas import GateMode, GateResult, GateVerdict

            render_result = GateResult(
                passed=True,
                verdict=GateVerdict.PASS,
                mode=GateMode.warn,
                evaluated_at=datetime.datetime.now(datetime.UTC).isoformat(),
            )
            mock_render_cls.return_value.evaluate = AsyncMock(return_value=render_result)

            data = ExportPreCheckRequest(html="<html></html>")
            resp = await service.pre_check(data)

            assert resp.qa.passed is True
            assert resp.rendering is not None
            assert resp.rendering.passed is True
            assert resp.can_export is True

    @pytest.mark.asyncio()
    async def test_pre_check_can_export_false_when_qa_blocks(self, mock_db: AsyncMock) -> None:
        """Pre-check can_export=False when QA gate blocks."""
        from app.connectors.qa_gate_schemas import ExportPreCheckRequest
        from app.connectors.service import ConnectorService

        service = ConnectorService(mock_db)

        qa_result = QAGateResult(
            passed=False,
            verdict=QAGateVerdict.BLOCK,
            mode=QAGateMode.enforce,
            evaluated_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )

        with (
            patch("app.connectors.qa_gate.ExportQAGate") as mock_qa_cls,
            patch("app.connectors.service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.rendering.gate_mode = "skip"
            mock_qa_cls.return_value.evaluate = AsyncMock(return_value=qa_result)

            data = ExportPreCheckRequest(html="<html></html>")
            resp = await service.pre_check(data)

            assert resp.qa.passed is False
            assert resp.can_export is False
