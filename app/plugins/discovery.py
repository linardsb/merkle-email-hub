"""Plugin discovery — scans directories for plugin manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from app.core.logging import get_logger
from app.plugins.manifest import PluginManifest

logger = get_logger(__name__)


class PluginDiscovery:
    """Scans a directory for plugin manifests."""

    def discover(self, plugin_dir: Path) -> list[PluginManifest]:
        """Scan plugin_dir for subdirectories containing plugin.yaml or plugin.json."""
        manifests: list[PluginManifest] = []
        if not plugin_dir.is_dir():
            logger.info("plugins.directory_not_found", path=str(plugin_dir))
            return manifests

        for child in sorted(plugin_dir.iterdir()):
            if not child.is_dir():
                continue
            manifest = self._load_manifest(child)
            if manifest is not None:
                manifests.append(manifest)
        return manifests

    def _load_manifest(self, plugin_path: Path) -> PluginManifest | None:
        """Load and validate a single plugin manifest."""
        yaml_path = plugin_path / "plugin.yaml"
        json_path = plugin_path / "plugin.json"

        if yaml_path.is_file():
            return self._parse_yaml(yaml_path)
        if json_path.is_file():
            return self._parse_json(json_path)

        logger.debug("plugins.no_manifest", path=str(plugin_path))
        return None

    def _parse_yaml(self, path: Path) -> PluginManifest | None:
        try:
            data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
            return PluginManifest.model_validate(data)
        except Exception as exc:
            logger.warning("plugins.manifest_invalid", path=str(path), error=str(exc))
            return None

    def _parse_json(self, path: Path) -> PluginManifest | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return PluginManifest.model_validate(data)
        except Exception as exc:
            logger.warning("plugins.manifest_invalid", path=str(path), error=str(exc))
            return None
