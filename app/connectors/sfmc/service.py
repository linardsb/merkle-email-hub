"""SFMC connector service for exporting email templates as Content Areas."""

from __future__ import annotations

from typing import Any, ClassVar

from app.connectors._base import OAuthConnectorService
from app.core.config import Settings, get_settings
from app.core.credentials import CredentialPool

__all__ = ["SFMCConnectorService"]


class SFMCConnectorService(OAuthConnectorService):
    """Exports compiled email HTML to SFMC Content Builder via OAuth 2.0."""

    service_name: ClassVar[str] = "sfmc"
    label: ClassVar[str] = "SFMC"

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        pool: CredentialPool | None = None,
    ) -> None:
        super().__init__(settings=settings or get_settings(), pool=pool)

    def _resolve_base_url(self, settings: Settings) -> str:
        return settings.esp_sync.sfmc_base_url

    def _token_url(self) -> str:
        return f"{self._base_url}/v2/token"

    def _asset_url(self) -> str:
        return f"{self._base_url}/asset/v1/content/assets"

    def _build_payload(self, *, html: str, name: str) -> dict[str, Any]:
        return {"name": name, "content": html}

    def _external_id_from_response(self, body: dict[str, Any]) -> str:
        return str(body["id"])

    def _mock_external_id(self, name: str) -> str:
        return f"sfmc_ca_{name.lower().replace(' ', '_')}"
