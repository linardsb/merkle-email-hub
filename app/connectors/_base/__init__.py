"""Shared ABCs for ESP connector services."""

from app.connectors._base.api_key import ApiKeyConnectorService
from app.connectors._base.oauth import OAuthConnectorService

__all__ = ["ApiKeyConnectorService", "OAuthConnectorService"]
