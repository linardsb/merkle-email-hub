"""Figma webhook registration and debounced sync handling."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.core.config import get_settings
from app.core.logging import get_logger
from app.design_sync.crypto import decrypt_token
from app.design_sync.exceptions import (
    ConnectionNotFoundError,
    SyncFailedError,
    UnsupportedProviderError,
)
from app.design_sync.figma.service import FigmaDesignSyncService
from app.design_sync.schemas import TokenDiffEntry

if TYPE_CHECKING:
    from app.auth.models import User
    from app.design_sync.schemas import DesignSyncUpdateMessage
    from app.design_sync.services._context import DesignSyncContext


logger = get_logger(__name__)


class WebhookService:
    """Figma webhook registration + sync triggered by webhook events."""

    def __init__(self, ctx: DesignSyncContext) -> None:
        self._ctx = ctx

    async def register_figma_webhook(self, connection_id: int, *, team_id: str, user: User) -> str:
        """Register a Figma FILE_UPDATE webhook for a connection."""
        conn = await self._ctx.repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._ctx.verify_access(conn.project_id, user)
        if conn.provider != "figma":
            raise UnsupportedProviderError("Webhooks are only supported for Figma connections")

        access_token = decrypt_token(conn.encrypted_token)
        figma = FigmaDesignSyncService()
        settings = get_settings()

        callback_url = settings.design_sync.figma_webhook_callback_url
        if not callback_url:
            raise SyncFailedError("DESIGN_SYNC__FIGMA_WEBHOOK_CALLBACK_URL is not configured")

        webhook_id = await figma.register_webhook(
            access_token,
            team_id=team_id,
            endpoint=f"{callback_url}/api/v1/design-sync/webhooks/figma",
            passcode=settings.design_sync.figma_webhook_passcode,
        )
        await self._ctx.repo.update_webhook_id(conn, webhook_id)
        await self._ctx.db.commit()
        logger.info(
            "design_sync.webhook_registered",
            connection_id=connection_id,
            webhook_id=webhook_id,
        )
        return webhook_id

    async def unregister_figma_webhook(self, connection_id: int, *, user: User) -> None:
        """Remove a Figma webhook for a connection."""
        conn = await self._ctx.repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._ctx.verify_access(conn.project_id, user)
        if not conn.webhook_id:
            return

        access_token = decrypt_token(conn.encrypted_token)
        figma = FigmaDesignSyncService()
        await figma.delete_webhook(access_token, conn.webhook_id)
        await self._ctx.repo.update_webhook_id(conn, None)
        await self._ctx.db.commit()
        logger.info("design_sync.webhook_unregistered", connection_id=connection_id)

    async def handle_webhook_sync(self, connection_id: int) -> DesignSyncUpdateMessage | None:
        """Run sync triggered by webhook, compute diff, return WS message if changes."""
        from app.design_sync.schemas import DesignSyncUpdateMessage
        from app.design_sync.services.connection_service import ConnectionService
        from app.design_sync.services.conversion_service import TokenConversionService

        conn = await self._ctx.repo.get_connection(connection_id)
        if conn is None:
            return None

        try:
            await ConnectionService(self._ctx).sync_connection(connection_id, user=None)
        except Exception:
            logger.warning(
                "design_sync.webhook_sync_failed",
                connection_id=connection_id,
                exc_info=True,
            )
            return None

        diff = await TokenConversionService(self._ctx).get_token_diff(connection_id)
        if not diff.entries:
            return None

        return DesignSyncUpdateMessage(
            connection_id=connection_id,
            diff_summary=format_diff_summary(diff.entries),
            total_changes=len(diff.entries),
            timestamp=datetime.now(UTC),
        )


def format_diff_summary(entries: list[TokenDiffEntry]) -> str:
    """Build a human-readable summary like '3 colors added, 1 removed'."""
    counts: Counter[str] = Counter()
    for e in entries:
        counts[e.change] += 1
    parts = [f"{count} {change}" for change, count in sorted(counts.items())]
    return ", ".join(parts) if parts else "no changes"
