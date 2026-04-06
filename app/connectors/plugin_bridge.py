"""Runtime registration bridge for plugin-provided ESP connectors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.connectors.protocol import ConnectorProvider
    from app.connectors.sync_protocol import ESPSyncProvider

logger = get_logger(__name__)


def register_plugin_connector(name: str, provider_cls: type[ConnectorProvider]) -> None:
    """Register a plugin-provided export connector at runtime."""
    from app.connectors.service import SUPPORTED_CONNECTORS

    if name in SUPPORTED_CONNECTORS:
        logger.warning("connectors.plugin_duplicate_export", name=name)
        return  # Built-in connectors take priority
    SUPPORTED_CONNECTORS[name] = provider_cls
    logger.info("connectors.plugin_export_registered", name=name)


def register_plugin_sync_provider(name: str, provider_cls: type[ESPSyncProvider]) -> None:
    """Register a plugin-provided sync provider at runtime."""
    from app.connectors.sync_service import PROVIDER_REGISTRY

    if name in PROVIDER_REGISTRY:
        logger.warning("connectors.plugin_duplicate_sync", name=name)
        return  # Built-in providers take priority
    PROVIDER_REGISTRY[name] = provider_cls
    logger.info("connectors.plugin_sync_registered", name=name)


def unregister_plugin_connector(name: str) -> None:
    """Remove a plugin connector from both registries."""
    from app.connectors.service import SUPPORTED_CONNECTORS
    from app.connectors.sync_service import PROVIDER_REGISTRY

    SUPPORTED_CONNECTORS.pop(name, None)
    PROVIDER_REGISTRY.pop(name, None)
