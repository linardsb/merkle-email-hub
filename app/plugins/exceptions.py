"""Plugin exception hierarchy."""

from app.core.exceptions import AppError


class PluginError(AppError):
    """Base exception for plugin subsystem."""


class PluginLoadError(PluginError):
    """Plugin failed to load (import error, timeout, bad entry point)."""


class PluginPermissionError(PluginError):
    """Plugin attempted an action it doesn't have permission for."""


class PluginConflictError(PluginError):
    """Two plugins register the same capability name."""


class PluginNotFoundError(PluginError):
    """Plugin not found in registry."""


class PluginTimeoutError(PluginError):
    """Plugin execution exceeded its timeout."""


class PluginHealthError(PluginError):
    """Plugin health check failed."""
