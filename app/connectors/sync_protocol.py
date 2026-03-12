"""Protocol interface for ESP bidirectional sync providers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.connectors.sync_schemas import ESPTemplate


@runtime_checkable
class ESPSyncProvider(Protocol):
    """Protocol that all ESP sync providers must implement.

    Each provider connects to an ESP's API to list, read, create, update, and delete
    email templates for bidirectional sync.
    """

    async def validate_credentials(self, credentials: dict[str, str]) -> bool:
        """Validate ESP credentials by making a test API call."""
        ...

    async def list_templates(self, credentials: dict[str, str]) -> list[ESPTemplate]:
        """List all templates available in the ESP."""
        ...

    async def get_template(self, template_id: str, credentials: dict[str, str]) -> ESPTemplate:
        """Get a single template by ID from the ESP."""
        ...

    async def create_template(
        self, name: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Create a new template in the ESP."""
        ...

    async def update_template(
        self, template_id: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Update an existing template in the ESP."""
        ...

    async def delete_template(self, template_id: str, credentials: dict[str, str]) -> bool:
        """Delete a template from the ESP. Returns True if successful."""
        ...
