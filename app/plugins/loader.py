"""Plugin loader — dynamic import with namespace isolation."""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path
from types import ModuleType

from app.core.logging import get_logger
from app.plugins.exceptions import PluginLoadError
from app.plugins.manifest import PluginManifest

logger = get_logger(__name__)

# Entry point must look like a package path (e.g. "my_plugin.main"), not a stdlib module
_ENTRY_POINT_RE = re.compile(r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)+$")

# Block imports of known dangerous stdlib/builtin modules
_BLOCKED_PREFIXES = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "shutil",
        "importlib",
        "builtins",
        "ctypes",
        "socket",
        "http",
        "multiprocessing",
        "signal",
    }
)


class PluginLoader:
    """Dynamically imports plugin modules.

    TRUST BOUNDARY: Plugins run in-process with full Python access. The entry point
    blocklist prevents accidental use of stdlib module names as entry points, but does
    NOT sandbox plugin code. Plugins can import any module once loaded. Only install
    plugins from trusted sources. Plugin management is restricted to admin users.
    """

    def load(self, manifest: PluginManifest, plugin_dir: Path) -> ModuleType:
        """Import the plugin's entry point module.

        The plugin directory is temporarily added to sys.path, then removed.
        The entry point module must export a `setup(hub: HubPluginAPI) -> None` function.
        """
        self._validate_entry_point(manifest)

        plugin_path = plugin_dir / manifest.name.replace(".", "-")
        if not plugin_path.is_dir():
            plugin_path = plugin_dir / manifest.name
            if not plugin_path.is_dir():
                raise PluginLoadError(f"Plugin directory not found: {manifest.name}")

        path_str = str(plugin_path)
        # Invalidate cached modules for the plugin's entry point namespace.
        # Only evict if the module is NOT part of stdlib/site-packages (i.e., has
        # a __file__ outside common installed package locations, or matches the
        # plugin's top-level name and doesn't appear to be a system module).
        entry_parts = manifest.entry_point.split(".")
        top_level = entry_parts[0]
        for key in list(sys.modules):
            if key == top_level or key.startswith(f"{top_level}."):
                mod = sys.modules.get(key)
                mod_file = getattr(mod, "__file__", None) if mod else None
                # Skip eviction for stdlib/site-packages modules
                if mod_file and ("site-packages" in mod_file or "lib/python" in mod_file):
                    continue
                sys.modules.pop(key, None)

        sys.path.insert(0, path_str)
        try:
            module = importlib.import_module(manifest.entry_point)
        except Exception as exc:
            raise PluginLoadError(
                f"Failed to import plugin '{manifest.name}' entry point '{manifest.entry_point}': {exc}"
            ) from exc
        finally:
            if path_str in sys.path:
                sys.path.remove(path_str)

        if not hasattr(module, "setup"):
            raise PluginLoadError(
                f"Plugin '{manifest.name}' entry point '{manifest.entry_point}' must export a `setup()` function"
            )

        if not callable(module.setup):
            raise PluginLoadError(f"Plugin '{manifest.name}' `setup` attribute is not callable")

        logger.info("plugins.loaded", plugin=manifest.name, entry_point=manifest.entry_point)
        return module

    def _validate_entry_point(self, manifest: PluginManifest) -> None:
        """Reject entry points that target stdlib or system modules."""
        ep = manifest.entry_point
        if not _ENTRY_POINT_RE.match(ep):
            raise PluginLoadError(
                f"Plugin '{manifest.name}' entry point '{ep}' must be a dotted Python module path (e.g. 'my_plugin.main')"
            )
        top_level = ep.split(".")[0]
        if top_level in _BLOCKED_PREFIXES:
            raise PluginLoadError(
                f"Plugin '{manifest.name}' entry point '{ep}' uses a blocked module prefix '{top_level}'"
            )
