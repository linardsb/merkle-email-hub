"""Tests for the fixed export route — template_version_id + build_id paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.connectors.schemas import ExportRequest


class TestExportRequestValidation:
    """Tests for ExportRequest schema validation."""

    def test_export_request_with_build_id(self) -> None:
        req = ExportRequest(build_id=1, content_block_name="email")
        assert req.build_id == 1
        assert req.template_version_id is None

    def test_export_request_with_template_version_id(self) -> None:
        req = ExportRequest(template_version_id=42)
        assert req.template_version_id == 42
        assert req.build_id is None

    def test_export_request_requires_at_least_one_id(self) -> None:
        with pytest.raises(ValidationError, match="Either build_id or template_version_id"):
            ExportRequest(connector_type="braze")

    def test_export_request_with_both_ids(self) -> None:
        req = ExportRequest(build_id=1, template_version_id=42)
        assert req.build_id == 1
        assert req.template_version_id == 42

    def test_content_block_name_defaults_to_email(self) -> None:
        req = ExportRequest(build_id=1)
        assert req.content_block_name == "email"


class TestConnectorServiceExport:
    """Tests for ConnectorService.export with both paths."""

    @pytest.mark.asyncio()
    async def test_export_with_template_version_id(self) -> None:
        from app.connectors.service import ConnectorService

        db = AsyncMock()
        mock_version = MagicMock()
        mock_version.html_source = "<html>Template content</html>"

        # Mock the DB query for TemplateVersion
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_version
        db.execute = AsyncMock(return_value=mock_result)

        service = ConnectorService(db=db)
        user = MagicMock()
        user.id = 1

        data = ExportRequest(template_version_id=42, connector_type="braze")
        response = await service.export(data, user)

        assert response.status == "success"
        assert response.template_version_id == 42
        assert response.external_id is not None

    @pytest.mark.asyncio()
    async def test_export_with_build_id_uses_compiled_html(self) -> None:
        from app.connectors.service import ConnectorService

        db = AsyncMock()
        mock_build = MagicMock()
        mock_build.project_id = 1
        mock_build.compiled_html = "<html>Built content</html>"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_build
        db.execute = AsyncMock(return_value=mock_result)

        mock_record = MagicMock()
        mock_record.id = 10
        mock_record.build_id = 5
        mock_record.connector_type = "braze"
        mock_record.status = "success"
        mock_record.external_id = "braze_cb_email"
        mock_record.error_message = None
        mock_record.created_at = MagicMock()

        service = ConnectorService(db=db)
        user = MagicMock()
        user.id = 1

        data = ExportRequest(build_id=5, connector_type="braze", content_block_name="test")

        with patch.object(service, "_resolve_html", AsyncMock(return_value="<html>ok</html>")):
            with patch("app.connectors.service.ExportRecord", return_value=mock_record):
                response = await service.export(data, user)

        assert response.status == "success"

    @pytest.mark.asyncio()
    async def test_export_fails_when_no_compiled_html(self) -> None:
        from app.connectors.exceptions import ExportFailedError
        from app.connectors.service import ConnectorService

        db = AsyncMock()
        mock_build = MagicMock()
        mock_build.project_id = 1
        mock_build.compiled_html = None  # No compiled HTML

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_build
        db.execute = AsyncMock(return_value=mock_result)

        service = ConnectorService(db=db)
        user = MagicMock()
        user.id = 1

        data = ExportRequest(build_id=5, connector_type="braze", content_block_name="test")

        with patch("app.connectors.service.ProjectService") as MockPS:
            MockPS.return_value.verify_project_access = AsyncMock()
            with pytest.raises(ExportFailedError, match="no compiled HTML"):
                await service._resolve_html(data, user)

    @pytest.mark.asyncio()
    async def test_export_fails_when_template_version_not_found(self) -> None:
        from app.connectors.service import ConnectorService
        from app.core.exceptions import NotFoundError

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        service = ConnectorService(db=db)
        user = MagicMock()
        user.id = 1

        data = ExportRequest(template_version_id=999)

        with pytest.raises(NotFoundError, match="Template version 999"):
            await service._resolve_html(data, user)
