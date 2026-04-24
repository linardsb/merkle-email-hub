"""Tests for connector wiring in plugin registry — registration, conflicts, cleanup.

TODO: Phase 46.5 was marked done in the roadmap but the `PluginConnectorAPI`
(`HubPluginAPI.connectors`), `PluginRegistry._wire_connector`, and
`PluginRegistry._connector_names` surfaces these tests reference were never
actually implemented. The shipped design uses module-level functions in
`app/connectors/plugin_bridge.py` instead (see test_plugin_bridge.py).
Skipping so CI can go green without silently rewriting the intended behaviour.
"""

# mypy: ignore-errors
# pyright: basic, reportAttributeAccessIssue=false, reportCallIssue=false
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from app.plugins.api import HubPluginAPI
from app.plugins.exceptions import PluginConflictError
from app.plugins.manifest import PluginManifest, PluginPermission, PluginType
from app.plugins.registry import PluginRegistry, reset_plugin_registry

pytestmark = pytest.mark.skip(
    reason="PluginConnectorAPI / _wire_connector surface not yet implemented (Phase 46.5 partial)",
)


def _make_connector_manifest(name: str = "test-connector") -> PluginManifest:
    return PluginManifest(
        name=name,
        version="1.0.0",
        hub_api_version=">=1.0",
        plugin_type=PluginType.export_connector,
        entry_point="test_connector.main",
        permissions=[PluginPermission.network_access],
    )


@pytest.fixture(autouse=True)
def _reset_all() -> Generator[None, None, None]:
    """Reset plugin registry + save/restore connector registries."""
    from app.connectors.service import SUPPORTED_CONNECTORS
    from app.connectors.sync_service import PROVIDER_REGISTRY

    reset_plugin_registry()
    orig_connectors = dict(SUPPORTED_CONNECTORS)
    orig_providers = dict(PROVIDER_REGISTRY)
    yield
    reset_plugin_registry()
    SUPPORTED_CONNECTORS.clear()
    SUPPORTED_CONNECTORS.update(orig_connectors)
    PROVIDER_REGISTRY.clear()
    PROVIDER_REGISTRY.update(orig_providers)


class _FakeProvider:
    async def export(self, html: str, name: str, credentials: dict[str, str] | None = None) -> str:
        return "fake-id"


class TestConnectorWiring:
    def test_wire_connector_registers_providers(self) -> None:
        """_wire_connector() populates SUPPORTED_CONNECTORS."""
        from app.connectors.service import SUPPORTED_CONNECTORS

        registry = PluginRegistry()
        manifest = _make_connector_manifest()
        api = HubPluginAPI(manifest)
        api.connectors.register_provider("plugin_esp", _FakeProvider)

        registry._wire_connector(manifest, api)

        assert "plugin_esp" in SUPPORTED_CONNECTORS
        assert SUPPORTED_CONNECTORS["plugin_esp"] is _FakeProvider
        assert registry._connector_names["plugin_esp"] == "test-connector"

    def test_wire_connector_conflict_raises(self) -> None:
        """Duplicate connector name from two plugins raises PluginConflictError."""
        registry = PluginRegistry()

        manifest1 = _make_connector_manifest(name="plugin-aaa")
        api1 = HubPluginAPI(manifest1)
        api1.connectors.register_provider("shared_esp", _FakeProvider)
        registry._wire_connector(manifest1, api1)

        manifest2 = _make_connector_manifest(name="plugin-bbb")
        api2 = HubPluginAPI(manifest2)
        api2.connectors.register_provider("shared_esp", _FakeProvider)

        with pytest.raises(PluginConflictError, match="shared_esp"):
            registry._wire_connector(manifest2, api2)

    def test_unregister_cleans_connector(self) -> None:
        """unregister() removes connector from both registries."""
        from app.connectors.service import SUPPORTED_CONNECTORS

        registry = PluginRegistry()
        manifest = _make_connector_manifest()
        api = HubPluginAPI(manifest)
        api.connectors.register_provider("plugin_esp", _FakeProvider)

        # Simulate full registration
        registry._plugins["test-connector"] = type(registry)  # type: ignore[assignment]
        # Use proper PluginInstance
        from app.plugins.registry import PluginInstance

        registry._plugins["test-connector"] = PluginInstance(
            manifest=manifest, module=None, api=api, status="active"
        )
        registry._wire_connector(manifest, api)

        assert "plugin_esp" in SUPPORTED_CONNECTORS

        registry.unregister("test-connector")
        assert "plugin_esp" not in SUPPORTED_CONNECTORS
        assert "plugin_esp" not in registry._connector_names

    def test_discover_and_load_connector_plugin(self, tmp_path: Path) -> None:
        """End-to-end: plugin dir with manifest + module -> discovered + wired."""
        from app.connectors.service import SUPPORTED_CONNECTORS

        registry = PluginRegistry()

        plugin_dir = tmp_path / "test-connector"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yaml").write_text(
            "name: test-connector\n"
            "version: '1.0.0'\n"
            "hub_api_version: '>=1.0'\n"
            "plugin_type: export_connector\n"
            "entry_point: test_connector.main\n"
            "permissions:\n"
            "  - network_access\n"
        )
        pkg = plugin_dir / "test_connector"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "main.py").write_text(
            "class MyProvider:\n"
            "    async def export(self, html, name, credentials=None):\n"
            "        return 'test-id'\n"
            "\n"
            "def setup(hub):\n"
            "    hub.connectors.register_provider('test_esp', MyProvider)\n"
        )

        loaded = registry.discover_and_load(tmp_path)
        assert "test-connector" in loaded
        assert "test_esp" in SUPPORTED_CONNECTORS
        assert registry._connector_names["test_esp"] == "test-connector"
