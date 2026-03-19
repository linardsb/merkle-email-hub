"""Central plugin registry — singleton that tracks loaded plugins."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

from app.core.logging import get_logger
from app.plugins.api import HubPluginAPI
from app.plugins.discovery import PluginDiscovery
from app.plugins.exceptions import PluginConflictError, PluginError, PluginNotFoundError
from app.plugins.loader import PluginLoader
from app.plugins.manifest import PluginManifest, PluginType
from app.plugins.sandbox import PluginSandbox
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)


@dataclass
class PluginInstance:
    manifest: PluginManifest
    module: ModuleType | None
    api: HubPluginAPI
    status: str = "active"  # active, disabled, error, inactive, degraded
    loaded_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None
    consecutive_failures: int = 0


class PluginRegistry:
    """Central registry for all loaded plugins."""

    def __init__(self, default_timeout_s: float = 30.0) -> None:
        self._plugins: dict[str, PluginInstance] = {}
        self._discovery = PluginDiscovery()
        self._loader = PluginLoader()
        self._qa_check_names: dict[str, str] = {}  # check_name -> plugin_name
        self._sandbox = PluginSandbox(default_timeout_s=default_timeout_s)

    @property
    def sandbox(self) -> PluginSandbox:
        return self._sandbox

    def discover_and_load(self, plugin_dir: Path) -> list[str]:
        """Discover, load, and register all plugins in the directory.

        Returns list of successfully loaded plugin names.
        """
        manifests = self._discovery.discover(plugin_dir)
        loaded: list[str] = []

        for manifest in manifests:
            try:
                self.load_and_register(manifest, plugin_dir)
                loaded.append(manifest.name)
            except Exception as exc:
                logger.warning(
                    "plugins.load_failed",
                    plugin=manifest.name,
                    error=str(exc),
                )
                self._plugins[manifest.name] = PluginInstance(
                    manifest=manifest,
                    module=None,
                    api=HubPluginAPI(manifest),
                    status="error",
                    error=str(exc),
                )
        return loaded

    def load_and_register(
        self,
        manifest: PluginManifest,
        plugin_dir: Path,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Load a single plugin and register it."""
        if manifest.name in self._plugins and self._plugins[manifest.name].status == "active":
            raise PluginConflictError(f"Plugin '{manifest.name}' is already registered")

        module = self._loader.load(manifest, plugin_dir)
        api = HubPluginAPI(manifest, config)

        # Call plugin's setup function
        module.setup(api)

        # Wire into subsystems based on type
        self._wire_plugin(manifest, api)

        self._plugins[manifest.name] = PluginInstance(
            manifest=manifest,
            module=module,
            api=api,
        )
        logger.info("plugins.registered", plugin=manifest.name, type=manifest.plugin_type.value)

    def _wire_plugin(self, manifest: PluginManifest, api: HubPluginAPI) -> None:
        """Register plugin capabilities with the appropriate subsystem."""
        if manifest.plugin_type == PluginType.qa_check:
            self._wire_qa_checks(manifest, api)

    def _wire_qa_checks(self, manifest: PluginManifest, api: HubPluginAPI) -> None:
        """Register plugin QA checks, detecting conflicts."""
        for check_name in api.qa.registered_checks:
            if check_name in self._qa_check_names:
                existing = self._qa_check_names[check_name]
                raise PluginConflictError(
                    f"QA check '{check_name}' already registered by plugin '{existing}'"
                )
            self._qa_check_names[check_name] = manifest.name

    def unregister(self, plugin_name: str) -> None:
        """Remove a plugin from the registry."""
        instance = self._plugins.pop(plugin_name, None)
        if instance is None:
            raise PluginNotFoundError(f"Plugin '{plugin_name}' not found")

        self._qa_check_names = {k: v for k, v in self._qa_check_names.items() if v != plugin_name}
        logger.info("plugins.unregistered", plugin=plugin_name)

    def disable(self, plugin_name: str) -> None:
        """Disable a plugin without removing it."""
        instance = self._plugins.get(plugin_name)
        if instance is None:
            raise PluginNotFoundError(f"Plugin '{plugin_name}' not found")
        instance.status = "disabled"
        self._qa_check_names = {k: v for k, v in self._qa_check_names.items() if v != plugin_name}
        logger.info("plugins.disabled", plugin=plugin_name)

    def enable(self, plugin_name: str) -> None:
        """Re-enable a disabled plugin."""
        instance = self._plugins.get(plugin_name)
        if instance is None:
            raise PluginNotFoundError(f"Plugin '{plugin_name}' not found")
        if instance.status == "error":
            raise PluginError(f"Plugin '{plugin_name}' is in error state, cannot enable")
        instance.status = "active"
        if instance.manifest.plugin_type == PluginType.qa_check:
            self._wire_qa_checks(instance.manifest, instance.api)
        logger.info("plugins.enabled", plugin=plugin_name)

    def get_plugin(self, plugin_name: str) -> PluginInstance:
        instance = self._plugins.get(plugin_name)
        if instance is None:
            raise PluginNotFoundError(f"Plugin '{plugin_name}' not found")
        return instance

    def list_plugins(self) -> list[PluginInstance]:
        return list(self._plugins.values())

    def get_active_qa_checks(
        self,
    ) -> dict[str, Callable[[str, QACheckConfig | None], Awaitable[QACheckResult]]]:
        """Return all QA check functions from active plugins."""
        checks: dict[str, Callable[[str, QACheckConfig | None], Awaitable[QACheckResult]]] = {}
        for name, plugin_name in self._qa_check_names.items():
            instance = self._plugins.get(plugin_name)
            if instance and instance.status == "active":
                fn = instance.api.qa.registered_checks.get(name)
                if fn:
                    checks[name] = fn
        return checks

    def get_plugin_name_for_check(self, check_name: str) -> str:
        """Return the plugin name that owns a QA check, or check_name itself as fallback."""
        return self._qa_check_names.get(check_name, check_name)

    def rewire_plugin(self, plugin_name: str) -> None:
        """Re-register plugin capabilities after restart."""
        instance = self._plugins.get(plugin_name)
        if instance is None:
            raise PluginNotFoundError(f"Plugin '{plugin_name}' not found")
        self._wire_plugin(instance.manifest, instance.api)


# Module-level singleton
_registry: PluginRegistry | None = None


def get_plugin_registry() -> PluginRegistry:
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


def reset_plugin_registry() -> None:
    """Reset for testing."""
    global _registry
    _registry = None
