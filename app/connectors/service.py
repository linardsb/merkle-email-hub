"""Business logic for ESP connector operations."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.braze.service import BrazeConnectorService
from app.connectors.exceptions import ExportFailedError, UnsupportedConnectorError
from app.connectors.models import ExportRecord
from app.connectors.schemas import ExportRequest, ExportResponse
from app.core.logging import get_logger

logger = get_logger(__name__)

SUPPORTED_CONNECTORS = {"braze"}


class ConnectorService:
    """Orchestrates exports to ESP connectors."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.braze = BrazeConnectorService()

    async def export(self, data: ExportRequest, user_id: int) -> ExportResponse:
        """Export an email build to the specified ESP."""
        if data.connector_type not in SUPPORTED_CONNECTORS:
            raise UnsupportedConnectorError(f"Connector '{data.connector_type}' is not supported")

        logger.info(
            "connectors.export_started", connector=data.connector_type, build_id=data.build_id
        )

        record = ExportRecord(
            build_id=data.build_id,
            connector_type=data.connector_type,
            exported_by_id=user_id,
            status="exporting",
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)

        try:
            # TODO: Fetch compiled HTML from build_id
            html_placeholder = "<html><body>Placeholder</body></html>"
            external_id = await self.braze.export(html_placeholder, data.content_block_name)
            record.status = "success"
            record.external_id = external_id
        except Exception as exc:
            record.status = "failed"
            record.error_message = str(exc)
            raise ExportFailedError(str(exc)) from exc
        finally:
            await self.db.commit()
            await self.db.refresh(record)

        logger.info("connectors.export_completed", record_id=record.id, status=record.status)
        return ExportResponse.model_validate(record)
