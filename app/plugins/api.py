"""Sandboxed API surface exposed to plugins with permission enforcement."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.core.logging import get_logger
from app.plugins.exceptions import PluginPermissionError
from app.plugins.manifest import PluginManifest, PluginPermission
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)


class PluginQAAPI:
    """QA check registration API for plugins."""

    def __init__(self, manifest: PluginManifest) -> None:
        self._manifest = manifest
        self._checks: dict[
            str, Callable[[str, QACheckConfig | None], Awaitable[QACheckResult]]
        ] = {}

    def register_check(
        self,
        name: str,
        check_fn: Callable[[str, QACheckConfig | None], Awaitable[QACheckResult]],
    ) -> None:
        """Register a QA check function."""
        self._checks[name] = check_fn
        logger.info("plugins.qa_check_registered", plugin=self._manifest.name, check=name)

    @property
    def registered_checks(
        self,
    ) -> dict[str, Callable[[str, QACheckConfig | None], Awaitable[QACheckResult]]]:
        return dict(self._checks)


class PluginConfigAPI:
    """Plugin configuration access."""

    def __init__(self, manifest: PluginManifest, config: dict[str, Any]) -> None:
        self._manifest = manifest
        self._config = config

    def get(self, key: str, default: object = None) -> object:
        return self._config.get(key, default)


class HubPluginAPI:
    """Sandboxed API surface exposed to plugins.

    Each sub-API enforces permissions from the manifest.
    """

    def __init__(self, manifest: PluginManifest, config: dict[str, Any] | None = None) -> None:
        self._manifest = manifest
        self.qa = PluginQAAPI(manifest)
        self.config = PluginConfigAPI(manifest, config or {})

    def _require_permission(self, permission: PluginPermission) -> None:
        if permission not in self._manifest.permissions:
            raise PluginPermissionError(
                f"Plugin '{self._manifest.name}' lacks '{permission.value}' permission"
            )

    @property
    def manifest(self) -> PluginManifest:
        return self._manifest
