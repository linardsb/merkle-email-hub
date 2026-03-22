"""Unit tests for the export approval gate (Phase 28.2)."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.connectors.approval_gate import ExportApprovalGate
from app.connectors.approval_gate_schemas import ApprovalGateResult
from app.connectors.exceptions import ApprovalRequiredError
from app.connectors.qa_gate_schemas import QAGateMode, QAGateResult, QAGateVerdict

# ── ExportApprovalGate.evaluate() ──


class TestExportApprovalGateEvaluate:
    """Tests for ExportApprovalGate.evaluate()."""

    @pytest.fixture()
    def mock_db(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture()
    def gate(self, mock_db: AsyncMock) -> ExportApprovalGate:
        return ExportApprovalGate(mock_db)

    @pytest.mark.asyncio()
    async def test_no_build_id_skips_approval(self, gate: ExportApprovalGate) -> None:
        """build_id=None → required=False, passed=True."""
        result = await gate.evaluate(build_id=None, project_id=1)
        assert result.required is False
        assert result.passed is True

    @pytest.mark.asyncio()
    async def test_project_not_requiring_approval_passes(self, gate: ExportApprovalGate) -> None:
        """Project with require_approval_for_export=False → skip."""
        with patch.object(gate, "_project_requires_approval", return_value=False):
            result = await gate.evaluate(build_id=1, project_id=1)
        assert result.required is False
        assert result.passed is True

    @pytest.mark.asyncio()
    async def test_no_approval_request_blocks(self, gate: ExportApprovalGate) -> None:
        """Required project, no ApprovalRequest → passed=False."""
        with (
            patch.object(gate, "_project_requires_approval", return_value=True),
            patch("app.approval.repository.ApprovalRepository") as mock_repo_cls,
        ):
            mock_repo_cls.return_value.get_latest_by_build_id = AsyncMock(return_value=None)
            result = await gate.evaluate(build_id=1, project_id=1)

        assert result.required is True
        assert result.passed is False
        assert result.reason == "No approval request submitted"

    @pytest.mark.asyncio()
    async def test_pending_approval_blocks(self, gate: ExportApprovalGate) -> None:
        """status=pending → passed=False."""
        approval = MagicMock()
        approval.id = 10
        approval.status = "pending"

        with (
            patch.object(gate, "_project_requires_approval", return_value=True),
            patch("app.approval.repository.ApprovalRepository") as mock_repo_cls,
        ):
            mock_repo_cls.return_value.get_latest_by_build_id = AsyncMock(return_value=approval)
            result = await gate.evaluate(build_id=1, project_id=1)

        assert result.required is True
        assert result.passed is False
        assert result.approval_id == 10
        assert result.reason == "Approval pending review"

    @pytest.mark.asyncio()
    async def test_approved_passes(self, gate: ExportApprovalGate) -> None:
        """status=approved → passed=True with metadata."""
        approval = MagicMock()
        approval.id = 10
        approval.status = "approved"
        approval.reviewed_by_id = 5
        approval.updated_at = datetime.datetime(2026, 3, 22, tzinfo=datetime.UTC)

        with (
            patch.object(gate, "_project_requires_approval", return_value=True),
            patch("app.approval.repository.ApprovalRepository") as mock_repo_cls,
        ):
            mock_repo_cls.return_value.get_latest_by_build_id = AsyncMock(return_value=approval)
            result = await gate.evaluate(build_id=1, project_id=1)

        assert result.required is True
        assert result.passed is True
        assert result.approval_id == 10
        assert result.approved_by == "5"
        assert result.approved_at is not None

    @pytest.mark.asyncio()
    async def test_rejected_blocks(self, gate: ExportApprovalGate) -> None:
        """status=rejected → passed=False."""
        approval = MagicMock()
        approval.id = 10
        approval.status = "rejected"

        with (
            patch.object(gate, "_project_requires_approval", return_value=True),
            patch("app.approval.repository.ApprovalRepository") as mock_repo_cls,
        ):
            mock_repo_cls.return_value.get_latest_by_build_id = AsyncMock(return_value=approval)
            result = await gate.evaluate(build_id=1, project_id=1)

        assert result.required is True
        assert result.passed is False
        assert result.reason == "Approval rejected"

    @pytest.mark.asyncio()
    async def test_revision_requested_blocks(self, gate: ExportApprovalGate) -> None:
        """status=revision_requested → passed=False."""
        approval = MagicMock()
        approval.id = 10
        approval.status = "revision_requested"

        with (
            patch.object(gate, "_project_requires_approval", return_value=True),
            patch("app.approval.repository.ApprovalRepository") as mock_repo_cls,
        ):
            mock_repo_cls.return_value.get_latest_by_build_id = AsyncMock(return_value=approval)
            result = await gate.evaluate(build_id=1, project_id=1)

        assert result.required is True
        assert result.passed is False
        assert result.reason == "Revisions requested"


# ── ConnectorService.export() integration ──


class TestApprovalGateIntegration:
    """Tests for approval gate integration in ConnectorService.export()."""

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

    def _pass_qa_result(self) -> QAGateResult:
        return QAGateResult(
            passed=True,
            verdict=QAGateVerdict.PASS,
            mode=QAGateMode.warn,
            evaluated_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )

    def _block_approval(self) -> ApprovalGateResult:
        return ApprovalGateResult(
            required=True, passed=False, reason="No approval request submitted"
        )

    def _pass_approval(self) -> ApprovalGateResult:
        return ApprovalGateResult(required=False, passed=True)

    @pytest.mark.asyncio()
    async def test_approval_required_no_request_raises(
        self, mock_db: AsyncMock, mock_user_dev: MagicMock
    ) -> None:
        """ApprovalRequiredError raised when approval is required but missing."""
        from app.connectors.schemas import ExportRequest
        from app.connectors.service import ConnectorService

        service = ConnectorService(mock_db)

        with (
            patch.object(service, "_resolve_html", return_value="<html></html>"),
            patch.object(service, "_resolve_project_id", return_value=1),
            patch("app.connectors.service.get_settings") as mock_settings,
            patch("app.connectors.qa_gate.ExportQAGate") as mock_qa_cls,
            patch("app.connectors.approval_gate.ExportApprovalGate") as mock_approval_cls,
        ):
            mock_settings.return_value.export.qa_gate_mode = "warn"
            mock_settings.return_value.rendering.gate_mode = "skip"
            mock_qa_cls.return_value.evaluate = AsyncMock(return_value=self._pass_qa_result())
            mock_approval_cls.return_value.evaluate = AsyncMock(return_value=self._block_approval())

            data = ExportRequest(build_id=1)
            with pytest.raises(ApprovalRequiredError):
                await service.export(data, mock_user_dev)

    @pytest.mark.asyncio()
    async def test_approval_not_required_proceeds(
        self, mock_db: AsyncMock, mock_user_dev: MagicMock
    ) -> None:
        """Export succeeds when project doesn't require approval."""
        from app.connectors.schemas import ExportRequest
        from app.connectors.service import ConnectorService

        service = ConnectorService(mock_db)

        with (
            patch.object(service, "_resolve_html", return_value="<html></html>"),
            patch.object(service, "_resolve_project_id", return_value=1),
            patch("app.connectors.service.get_settings") as mock_settings,
            patch("app.connectors.qa_gate.ExportQAGate") as mock_qa_cls,
            patch("app.connectors.approval_gate.ExportApprovalGate") as mock_approval_cls,
        ):
            mock_settings.return_value.export.qa_gate_mode = "warn"
            mock_settings.return_value.rendering.gate_mode = "skip"
            mock_qa_cls.return_value.evaluate = AsyncMock(return_value=self._pass_qa_result())
            mock_approval_cls.return_value.evaluate = AsyncMock(return_value=self._pass_approval())

            data = ExportRequest(template_version_id=1)
            resp = await service.export(data, mock_user_dev)
            assert resp.status == "success"
            assert resp.approval_result is not None
            assert resp.approval_result.passed is True

    @pytest.mark.asyncio()
    async def test_skip_approval_admin_proceeds(
        self, mock_db: AsyncMock, mock_user_admin: MagicMock
    ) -> None:
        """Admin skip_approval=True bypasses approval gate."""
        from app.connectors.schemas import ExportRequest
        from app.connectors.service import ConnectorService

        service = ConnectorService(mock_db)

        with (
            patch.object(service, "_resolve_html", return_value="<html></html>"),
            patch.object(service, "_resolve_project_id", return_value=1),
            patch("app.connectors.service.get_settings") as mock_settings,
            patch("app.connectors.qa_gate.ExportQAGate") as mock_qa_cls,
            patch("app.connectors.approval_gate.ExportApprovalGate") as mock_approval_cls,
        ):
            mock_settings.return_value.export.qa_gate_mode = "warn"
            mock_settings.return_value.rendering.gate_mode = "skip"
            mock_qa_cls.return_value.evaluate = AsyncMock(return_value=self._pass_qa_result())

            data = ExportRequest(template_version_id=1, skip_approval=True)
            resp = await service.export(data, mock_user_admin)

            mock_approval_cls.return_value.evaluate.assert_not_called()
            assert resp.approval_result is None

    @pytest.mark.asyncio()
    async def test_skip_approval_non_admin_forbidden(
        self, mock_db: AsyncMock, mock_user_dev: MagicMock
    ) -> None:
        """Non-admin skip_approval=True raises ForbiddenError."""
        from app.connectors.schemas import ExportRequest
        from app.connectors.service import ConnectorService
        from app.core.exceptions import ForbiddenError

        service = ConnectorService(mock_db)
        data = ExportRequest(template_version_id=1, skip_approval=True)

        with pytest.raises(ForbiddenError):
            await service.export(data, mock_user_dev)

    @pytest.mark.asyncio()
    async def test_template_version_export_skips_approval(
        self, mock_db: AsyncMock, mock_user_dev: MagicMock
    ) -> None:
        """template_version_id without build_id → approval gate returns not required."""
        from app.connectors.schemas import ExportRequest
        from app.connectors.service import ConnectorService

        service = ConnectorService(mock_db)

        # Approval gate should still be called but return required=False (no build_id)
        not_required = ApprovalGateResult(required=False, passed=True)

        with (
            patch.object(service, "_resolve_html", return_value="<html></html>"),
            patch.object(service, "_resolve_project_id", return_value=None),
            patch("app.connectors.service.get_settings") as mock_settings,
            patch("app.connectors.qa_gate.ExportQAGate") as mock_qa_cls,
            patch("app.connectors.approval_gate.ExportApprovalGate") as mock_approval_cls,
        ):
            mock_settings.return_value.export.qa_gate_mode = "warn"
            mock_settings.return_value.rendering.gate_mode = "skip"
            mock_qa_cls.return_value.evaluate = AsyncMock(return_value=self._pass_qa_result())
            mock_approval_cls.return_value.evaluate = AsyncMock(return_value=not_required)

            data = ExportRequest(template_version_id=1)
            resp = await service.export(data, mock_user_dev)
            assert resp.status == "success"

    @pytest.mark.asyncio()
    async def test_qa_passes_rendering_passes_approval_blocks(
        self, mock_db: AsyncMock, mock_user_dev: MagicMock
    ) -> None:
        """All gates run, approval blocks last."""
        from app.connectors.schemas import ExportRequest
        from app.connectors.service import ConnectorService
        from app.rendering.gate_schemas import GateMode, GateResult, GateVerdict

        service = ConnectorService(mock_db)

        render_pass = GateResult(
            passed=True,
            verdict=GateVerdict.PASS,
            mode=GateMode.warn,
            evaluated_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )

        with (
            patch.object(service, "_resolve_html", return_value="<html></html>"),
            patch.object(service, "_resolve_project_id", return_value=1),
            patch("app.connectors.service.get_settings") as mock_settings,
            patch("app.connectors.qa_gate.ExportQAGate") as mock_qa_cls,
            patch("app.rendering.gate.RenderingSendGate") as mock_render_cls,
            patch("app.connectors.approval_gate.ExportApprovalGate") as mock_approval_cls,
        ):
            mock_settings.return_value.export.qa_gate_mode = "warn"
            mock_settings.return_value.rendering.gate_mode = "warn"
            mock_qa_cls.return_value.evaluate = AsyncMock(return_value=self._pass_qa_result())
            mock_render_cls.return_value.evaluate = AsyncMock(return_value=render_pass)
            mock_approval_cls.return_value.evaluate = AsyncMock(return_value=self._block_approval())

            data = ExportRequest(build_id=1)
            with pytest.raises(ApprovalRequiredError):
                await service.export(data, mock_user_dev)

    @pytest.mark.asyncio()
    async def test_pre_check_includes_approval_result(self, mock_db: AsyncMock) -> None:
        """pre_check() returns approval field when build_id provided."""
        from app.connectors.qa_gate_schemas import ExportPreCheckRequest
        from app.connectors.service import ConnectorService

        service = ConnectorService(mock_db)

        with (
            patch("app.connectors.qa_gate.ExportQAGate") as mock_qa_cls,
            patch("app.connectors.service.get_settings") as mock_settings,
            patch("app.connectors.approval_gate.ExportApprovalGate") as mock_approval_cls,
        ):
            mock_settings.return_value.rendering.gate_mode = "skip"
            mock_qa_cls.return_value.evaluate = AsyncMock(return_value=self._pass_qa_result())
            mock_approval_cls.return_value.evaluate = AsyncMock(return_value=self._block_approval())

            data = ExportPreCheckRequest(html="<html></html>", build_id=1, project_id=1)
            resp = await service.pre_check(data)

            assert resp.approval is not None
            assert resp.approval.passed is False
            assert resp.can_export is False
