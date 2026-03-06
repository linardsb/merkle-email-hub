"""Business logic for ESP connector operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.connectors.adobe.service import AdobeConnectorService
from app.connectors.braze.service import BrazeConnectorService
from app.connectors.exceptions import ExportFailedError, UnsupportedConnectorError
from app.connectors.models import ExportRecord
from app.connectors.protocol import ConnectorProvider
from app.connectors.schemas import ExportRequest, ExportResponse
from app.connectors.sfmc.service import SFMCConnectorService
from app.connectors.taxi.service import TaxiConnectorService
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.email_engine.models import EmailBuild
from app.projects.service import ProjectService

logger = get_logger(__name__)

SUPPORTED_CONNECTORS: dict[str, type[ConnectorProvider]] = {
    "braze": BrazeConnectorService,
    "sfmc": SFMCConnectorService,
    "adobe_campaign": AdobeConnectorService,
    "taxi": TaxiConnectorService,
}


class ConnectorService:
    """Orchestrates exports to ESP connectors."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._providers: dict[str, ConnectorProvider] = {}

    def _get_provider(self, connector_type: str) -> ConnectorProvider:
        """Get or create a connector provider instance."""
        if connector_type not in self._providers:
            provider_cls = SUPPORTED_CONNECTORS.get(connector_type)
            if provider_cls is None:
                raise UnsupportedConnectorError(
                    f"Connector '{connector_type}' is not supported. "
                    f"Supported: {', '.join(sorted(SUPPORTED_CONNECTORS))}"
                )
            self._providers[connector_type] = provider_cls()
        return self._providers[connector_type]

    async def export(self, data: ExportRequest, user: User) -> ExportResponse:
        """Export an email build to the specified ESP."""
        # BOLA: verify user has access to the build's project
        result = await self.db.execute(select(EmailBuild).where(EmailBuild.id == data.build_id))
        build = result.scalar_one_or_none()
        if not build:
            raise NotFoundError(f"Build {data.build_id} not found")

        project_service = ProjectService(self.db)
        await project_service.verify_project_access(build.project_id, user)

        provider = self._get_provider(data.connector_type)

        logger.info(
            "connectors.export_started",
            connector=data.connector_type,
            build_id=data.build_id,
        )

        record = ExportRecord(
            build_id=data.build_id,
            connector_type=data.connector_type,
            exported_by_id=user.id,
            status="exporting",
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)

        try:
            # TODO: Fetch compiled HTML from build_id
            html_placeholder = "<html><body>Placeholder</body></html>"
            external_id = await provider.export(html_placeholder, data.content_block_name)
            record.status = "success"
            record.external_id = external_id
        except Exception as exc:
            record.status = "failed"
            record.error_message = "Export failed"
            logger.error(
                "connectors.export_error",
                record_id=record.id,
                connector=data.connector_type,
                error=str(exc),
                error_type=type(exc).__name__,
                exc_info=True,
            )
            raise ExportFailedError("Export operation failed") from exc
        finally:
            await self.db.commit()
            await self.db.refresh(record)

        logger.info(
            "connectors.export_completed",
            record_id=record.id,
            connector=data.connector_type,
            status=record.status,
        )
        return ExportResponse.model_validate(record)
