"""Sketch design sync provider — stub implementation."""

from __future__ import annotations

from app.design_sync.protocol import ExtractedTokens


class SketchDesignSyncService:
    """Stub Sketch provider. Returns empty tokens."""

    async def validate_connection(self, file_ref: str, access_token: str) -> bool:  # noqa: ARG002
        """Sketch validation always succeeds (stub)."""
        return True

    async def sync_tokens(self, file_ref: str, access_token: str) -> ExtractedTokens:  # noqa: ARG002
        """Sketch sync returns empty tokens (stub)."""
        return ExtractedTokens()
