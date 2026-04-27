"""Adobe Campaign connector service for exporting email templates as deliveries."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from app.connectors._base import OAuthConnectorService
from app.core.config import Settings, get_settings
from app.core.credentials import CredentialPool

__all__ = ["AdobeConnectorService"]


class AdobeConnectorService(OAuthConnectorService):
    """Exports compiled email HTML to Adobe Campaign via IMS OAuth."""

    service_name: ClassVar[str] = "adobe_campaign"
    label: ClassVar[str] = "Adobe Campaign"
    auth_request_encoding: ClassVar[Literal["json", "form"]] = "form"
    default_token_ttl: ClassVar[float] = 86399.0

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        pool: CredentialPool | None = None,
    ) -> None:
        super().__init__(settings=settings or get_settings(), pool=pool)

    def _resolve_base_url(self, settings: Settings) -> str:
        return settings.esp_sync.adobe_base_url

    def _token_url(self) -> str:
        return f"{self._base_url}/ims/token/v3"

    def _asset_url(self) -> str:
        return f"{self._base_url}/profileAndServicesExt/delivery"

    def _build_payload(self, *, html: str, name: str) -> dict[str, Any]:
        return {"label": name, "content": html}

    def _external_id_from_response(self, body: dict[str, Any]) -> str:
        return str(body["PKey"])

    def _mock_external_id(self, name: str) -> str:
        return f"adobe_dl_{name.lower().replace(' ', '_')}"
