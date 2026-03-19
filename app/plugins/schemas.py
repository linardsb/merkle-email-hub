"""Request/response schemas for plugin admin API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.plugins.manifest import PluginPermission, PluginType


class PluginInfoResponse(BaseModel):
    name: str
    version: str
    plugin_type: PluginType
    permissions: list[PluginPermission]
    status: str
    loaded_at: datetime | None = None
    error: str | None = None
    description: str = ""
    author: str = ""
    tags: list[str] = []


class PluginListResponse(BaseModel):
    plugins: list[PluginInfoResponse]
    total: int


class PluginHealthResponse(BaseModel):
    name: str
    status: str  # healthy, degraded, unhealthy
    message: str | None = None
    latency_ms: float = 0.0


class PluginHealthSummaryResponse(BaseModel):
    plugins: list[PluginHealthResponse]
    total: int
    healthy: int
    degraded: int
    unhealthy: int
