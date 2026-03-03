"""Protocol interface for ESP connector implementations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ConnectorProvider(Protocol):
    """Protocol that all ESP connector services must implement.

    Each connector packages compiled email HTML into the ESP's native format
    and returns a mock external ID (real API integration deferred to production).
    """

    async def export(self, html: str, name: str) -> str:
        """Export compiled HTML to the ESP.

        Args:
            html: Compiled email HTML from Maizzle build.
            name: User-provided name for the content block/template.

        Returns:
            External ID string from the ESP (mock for placeholder implementations).
        """
        ...
