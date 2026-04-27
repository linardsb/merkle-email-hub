"""Braze connector service for exporting email templates as Content Blocks."""

from __future__ import annotations

from typing import Any, ClassVar

from app.connectors._base import ApiKeyConnectorService
from app.core.config import Settings, get_settings
from app.core.credentials import CredentialPool

__all__ = ["BrazeConnectorService"]


class BrazeConnectorService(ApiKeyConnectorService):
    """Exports compiled email HTML to Braze as Content Blocks with Liquid."""

    service_name: ClassVar[str] = "braze"
    label: ClassVar[str] = "Braze"

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        pool: CredentialPool | None = None,
    ) -> None:
        super().__init__(settings=settings or get_settings(), pool=pool)

    def _resolve_base_url(self, settings: Settings) -> str:
        return settings.esp_sync.braze_base_url

    def _endpoint(self) -> str:
        return f"{self._base_url}/content_blocks/create"

    def _auth_header(self, api_key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {api_key}"}

    def _build_payload(self, *, html: str, name: str) -> dict[str, Any]:
        return {"name": name, "content": html, "tags": ["email-hub"]}

    def _external_id_from_response(self, body: dict[str, Any]) -> str:
        return str(body["content_block_id"])

    def _mock_external_id(self, name: str) -> str:
        return f"braze_cb_{name.lower().replace(' ', '_')}"
