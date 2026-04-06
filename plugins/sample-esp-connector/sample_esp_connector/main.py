"""Sample ESP connector plugin demonstrating the connector plugin API."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.plugins.api import HubPluginAPI


class SampleConnectorProvider:
    """Mock ESP connector for demonstration."""

    async def export(
        self,
        html: str,  # noqa: ARG002
        name: str,  # noqa: ARG002
        credentials: dict[str, str] | None = None,  # noqa: ARG002
    ) -> str:
        return f"sample-{uuid.uuid4().hex[:12]}"


def setup(hub: HubPluginAPI) -> None:
    """Plugin entry point."""
    hub.connectors.register_provider("sample_esp", SampleConnectorProvider)
