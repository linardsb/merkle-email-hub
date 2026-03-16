"""Taxi for Email sync provider — bidirectional template sync via Taxi API."""

from __future__ import annotations

import httpx

from app.connectors.http_resilience import resilient_request
from app.connectors.sync_schemas import ESPTemplate
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class TaxiSyncProvider:
    """Implements ESPSyncProvider for Taxi for Email.

    Credentials: ``{"api_key": "..."}``

    Auth: ``X-API-Key`` header on all requests.
    """

    _base_url: str

    def __init__(self, settings: Settings | None = None) -> None:
        _settings = settings or get_settings()
        self._base_url = _settings.esp_sync.taxi_base_url

    def _headers(self, credentials: dict[str, str]) -> dict[str, str]:
        return {"X-API-Key": credentials["api_key"]}

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    async def validate_credentials(self, credentials: dict[str, str]) -> bool:
        """Validate by listing templates (lightweight call)."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await resilient_request(
                    client,
                    "GET",
                    f"{self._base_url}/api/v1/templates",
                    headers=self._headers(credentials),
                    params={"per_page": 1},
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            logger.warning("taxi.sync.validate_failed", exc_info=True)
            return False

    async def list_templates(self, credentials: dict[str, str]) -> list[ESPTemplate]:
        """List all Taxi templates."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await resilient_request(
                client,
                "GET",
                f"{self._base_url}/api/v1/templates",
                headers=self._headers(credentials),
                params={"per_page": 1000, "page": 1},
            )
            resp.raise_for_status()
            data = resp.json()
        return [
            ESPTemplate(
                id=str(t["id"]),
                name=t["name"],
                html=t.get("content", ""),
                esp_type="taxi",
                created_at=t.get("created_at", ""),
                updated_at=t.get("updated_at", ""),
            )
            for t in data.get("templates", [])
        ]

    async def get_template(self, template_id: str, credentials: dict[str, str]) -> ESPTemplate:
        """Get a single Taxi template."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "GET",
                f"{self._base_url}/api/v1/templates/{template_id}",
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            t = resp.json()
        return ESPTemplate(
            id=str(t["id"]),
            name=t["name"],
            html=t.get("content", ""),
            esp_type="taxi",
            created_at=t.get("created_at", ""),
            updated_at=t.get("updated_at", ""),
        )

    async def create_template(
        self, name: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Create a new template in Taxi."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "POST",
                f"{self._base_url}/api/v1/templates",
                json={"name": name, "content": html},
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            t = resp.json()
        return ESPTemplate(
            id=str(t["id"]),
            name=t.get("name", name),
            html=t.get("content", html),
            esp_type="taxi",
            created_at=t.get("created_at", ""),
            updated_at=t.get("updated_at", ""),
        )

    async def update_template(
        self, template_id: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Update a Taxi template's content."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "PUT",
                f"{self._base_url}/api/v1/templates/{template_id}",
                json={"content": html},
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            t = resp.json()
        return ESPTemplate(
            id=str(t["id"]),
            name=t.get("name", ""),
            html=t.get("content", html),
            esp_type="taxi",
            created_at=t.get("created_at", ""),
            updated_at=t.get("updated_at", ""),
        )

    async def delete_template(self, template_id: str, credentials: dict[str, str]) -> bool:
        """Delete a Taxi template."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "DELETE",
                f"{self._base_url}/api/v1/templates/{template_id}",
                headers=self._headers(credentials),
            )
            return resp.status_code == 200
