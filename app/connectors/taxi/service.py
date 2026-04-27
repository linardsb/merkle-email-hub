"""Taxi for Email connector service for exporting templates with Taxi Syntax."""

from __future__ import annotations

from typing import Any, ClassVar

from app.connectors._base import ApiKeyConnectorService
from app.core.config import Settings, get_settings
from app.core.credentials import CredentialPool

__all__ = ["TaxiConnectorService"]


class TaxiConnectorService(ApiKeyConnectorService):
    """Exports compiled email HTML wrapped in Taxi Syntax via the Taxi API."""

    service_name: ClassVar[str] = "taxi"
    label: ClassVar[str] = "Taxi"

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        pool: CredentialPool | None = None,
    ) -> None:
        super().__init__(settings=settings or get_settings(), pool=pool)

    def _resolve_base_url(self, settings: Settings) -> str:
        return settings.esp_sync.taxi_base_url

    def _endpoint(self) -> str:
        return f"{self._base_url}/api/v1/templates"

    def _auth_header(self, api_key: str) -> dict[str, str]:
        return {"X-API-Key": api_key}

    def _build_payload(self, *, html: str, name: str) -> dict[str, Any]:
        return {"name": name, "content": html}

    def _external_id_from_response(self, body: dict[str, Any]) -> str:
        return str(body["id"])

    def _mock_external_id(self, name: str) -> str:
        return f"taxi_tpl_{name.lower().replace(' ', '_')}"
