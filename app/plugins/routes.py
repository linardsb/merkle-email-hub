"""Admin endpoints for plugin management."""

from fastapi import APIRouter, Depends, status
from fastapi.requests import Request

from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.rate_limit import limiter
from app.plugins.registry import PluginInstance, get_plugin_registry
from app.plugins.schemas import (
    PluginHealthResponse,
    PluginHealthSummaryResponse,
    PluginInfoResponse,
    PluginListResponse,
)

router = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])

_admin = require_role("admin")


def _to_response(instance: PluginInstance) -> PluginInfoResponse:
    return PluginInfoResponse(
        name=instance.manifest.name,
        version=instance.manifest.version,
        plugin_type=instance.manifest.plugin_type,
        permissions=instance.manifest.permissions,
        status=instance.status,
        loaded_at=instance.loaded_at,
        error=instance.error,
        description=instance.manifest.metadata.description,
        author=instance.manifest.metadata.author,
        tags=instance.manifest.metadata.tags,
    )


@router.get("", response_model=PluginListResponse)
@limiter.limit("60/minute")
async def list_plugins(
    request: Request,
    _user: User = Depends(_admin),
) -> PluginListResponse:
    """List all discovered plugins with status."""
    registry = get_plugin_registry()
    plugins = [_to_response(p) for p in registry.list_plugins()]
    return PluginListResponse(plugins=plugins, total=len(plugins))


@router.get("/health", response_model=PluginHealthSummaryResponse)
@limiter.limit("60/minute")
async def all_plugins_health(
    request: Request,
    _user: User = Depends(_admin),
) -> PluginHealthSummaryResponse:
    """Health summary for all plugins."""
    registry = get_plugin_registry()
    sandbox = registry.sandbox
    results: list[PluginHealthResponse] = []
    for instance in registry.list_plugins():
        if instance.status in ("active", "degraded"):
            health_fn = getattr(instance.module, "health", None) if instance.module else None
            health = await sandbox.health_check(instance.manifest.name, health_fn)
            results.append(
                PluginHealthResponse(
                    name=instance.manifest.name,
                    status=health.status,
                    message=health.message,
                    latency_ms=health.latency_ms,
                )
            )
        else:
            results.append(
                PluginHealthResponse(
                    name=instance.manifest.name,
                    status="unhealthy",
                    message=f"Plugin status: {instance.status}",
                )
            )
    return PluginHealthSummaryResponse(
        plugins=results,
        total=len(results),
        healthy=sum(1 for r in results if r.status == "healthy"),
        degraded=sum(1 for r in results if r.status == "degraded"),
        unhealthy=sum(1 for r in results if r.status == "unhealthy"),
    )


@router.get("/{plugin_name}", response_model=PluginInfoResponse)
@limiter.limit("60/minute")
async def get_plugin(
    request: Request,
    plugin_name: str,
    _user: User = Depends(_admin),
) -> PluginInfoResponse:
    """Get details for a specific plugin."""
    registry = get_plugin_registry()
    return _to_response(registry.get_plugin(plugin_name))


@router.get("/{plugin_name}/health", response_model=PluginHealthResponse)
@limiter.limit("60/minute")
async def plugin_health(
    request: Request,
    plugin_name: str,
    _user: User = Depends(_admin),
) -> PluginHealthResponse:
    """Health check for a specific plugin."""
    registry = get_plugin_registry()
    instance = registry.get_plugin(plugin_name)
    sandbox = registry.sandbox
    health_fn = getattr(instance.module, "health", None) if instance.module else None
    health = await sandbox.health_check(plugin_name, health_fn)
    return PluginHealthResponse(
        name=plugin_name,
        status=health.status,
        message=health.message,
        latency_ms=health.latency_ms,
    )


@router.post("/{plugin_name}/restart", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def restart_plugin(
    request: Request,
    plugin_name: str,
    _user: User = Depends(_admin),
) -> PluginInfoResponse:
    """Restart a plugin (shutdown -> startup)."""
    from app.plugins.lifecycle import PluginLifecycleManager

    registry = get_plugin_registry()
    instance = registry.get_plugin(plugin_name)
    sandbox = registry.sandbox
    lifecycle = PluginLifecycleManager(registry, sandbox)
    await lifecycle.restart(instance)
    # Re-wire subsystems after restart
    registry.rewire_plugin(plugin_name)
    return _to_response(registry.get_plugin(plugin_name))


@router.post("/{plugin_name}/enable", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def enable_plugin(
    request: Request,
    plugin_name: str,
    _user: User = Depends(_admin),
) -> PluginInfoResponse:
    """Enable a disabled plugin."""
    registry = get_plugin_registry()
    registry.enable(plugin_name)
    return _to_response(registry.get_plugin(plugin_name))


@router.post("/{plugin_name}/disable", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def disable_plugin(
    request: Request,
    plugin_name: str,
    _user: User = Depends(_admin),
) -> PluginInfoResponse:
    """Disable a plugin without removing it."""
    registry = get_plugin_registry()
    registry.disable(plugin_name)
    return _to_response(registry.get_plugin(plugin_name))


@router.delete("/{plugin_name}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_plugin(
    request: Request,
    plugin_name: str,
    _user: User = Depends(_admin),
) -> None:
    """Unregister and remove a plugin."""
    registry = get_plugin_registry()
    registry.unregister(plugin_name)
