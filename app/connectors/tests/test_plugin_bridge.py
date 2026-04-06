"""Tests for plugin connector bridge — runtime registration into both registries."""

from __future__ import annotations

import pytest

from app.connectors.plugin_bridge import (
    register_plugin_connector,
    register_plugin_sync_provider,
    unregister_plugin_connector,
)
from app.connectors.protocol import ConnectorProvider


class _MockProvider:
    """Minimal ConnectorProvider implementation for testing."""

    async def export(self, html: str, name: str, credentials: dict[str, str] | None = None) -> str:
        return f"mock-{name}"


class _MockSyncProvider:
    """Minimal ESPSyncProvider implementation for testing."""

    async def validate_credentials(self, credentials: dict[str, str]) -> bool:
        return True

    async def list_templates(self, credentials: dict[str, str]) -> list:
        return []

    async def get_template(self, template_id: str, credentials: dict[str, str]) -> object:
        return None  # type: ignore[return-value]

    async def create_template(self, name: str, html: str, credentials: dict[str, str]) -> object:
        return None  # type: ignore[return-value]

    async def update_template(
        self, template_id: str, html: str, credentials: dict[str, str]
    ) -> object:
        return None  # type: ignore[return-value]

    async def delete_template(self, template_id: str, credentials: dict[str, str]) -> bool:
        return True


@pytest.fixture(autouse=True)
def _isolate_registries() -> None:  # type: ignore[misc]
    """Save/restore both registries to prevent test pollution."""
    from app.connectors.service import SUPPORTED_CONNECTORS
    from app.connectors.sync_service import PROVIDER_REGISTRY

    orig_connectors = dict(SUPPORTED_CONNECTORS)
    orig_providers = dict(PROVIDER_REGISTRY)
    yield  # type: ignore[misc]
    SUPPORTED_CONNECTORS.clear()
    SUPPORTED_CONNECTORS.update(orig_connectors)
    PROVIDER_REGISTRY.clear()
    PROVIDER_REGISTRY.update(orig_providers)


class TestPluginBridge:
    def test_register_plugin_connector(self) -> None:
        from app.connectors.service import SUPPORTED_CONNECTORS

        register_plugin_connector("test_esp", _MockProvider)
        assert "test_esp" in SUPPORTED_CONNECTORS
        assert SUPPORTED_CONNECTORS["test_esp"] is _MockProvider

    def test_register_plugin_sync_provider(self) -> None:
        from app.connectors.sync_service import PROVIDER_REGISTRY

        register_plugin_sync_provider("test_esp", _MockSyncProvider)
        assert "test_esp" in PROVIDER_REGISTRY
        assert PROVIDER_REGISTRY["test_esp"] is _MockSyncProvider

    def test_duplicate_export_connector_skipped(self) -> None:
        """Built-in connectors take priority — duplicates are silently skipped."""
        from app.connectors.service import SUPPORTED_CONNECTORS

        original_cls = SUPPORTED_CONNECTORS["braze"]
        register_plugin_connector("braze", _MockProvider)
        assert SUPPORTED_CONNECTORS["braze"] is original_cls

    def test_duplicate_sync_provider_skipped(self) -> None:
        """Built-in sync providers take priority."""
        from app.connectors.sync_service import PROVIDER_REGISTRY

        original_cls = PROVIDER_REGISTRY["braze"]
        register_plugin_sync_provider("braze", _MockSyncProvider)
        assert PROVIDER_REGISTRY["braze"] is original_cls

    def test_unregister_plugin_connector(self) -> None:
        """Unregister removes from both registries."""
        from app.connectors.service import SUPPORTED_CONNECTORS
        from app.connectors.sync_service import PROVIDER_REGISTRY

        register_plugin_connector("test_esp", _MockProvider)
        register_plugin_sync_provider("test_esp", _MockSyncProvider)

        unregister_plugin_connector("test_esp")
        assert "test_esp" not in SUPPORTED_CONNECTORS
        assert "test_esp" not in PROVIDER_REGISTRY

    @pytest.mark.asyncio
    async def test_plugin_connector_export_works(self) -> None:
        """End-to-end: register → instantiate → call export()."""
        register_plugin_connector("test_esp", _MockProvider)

        from app.connectors.service import SUPPORTED_CONNECTORS

        provider_cls = SUPPORTED_CONNECTORS["test_esp"]
        provider = provider_cls()
        result = await provider.export("<h1>Hello</h1>", "test-email")
        assert result == "mock-test-email"
        assert isinstance(provider, ConnectorProvider)
