"""Sketch design sync provider — stub implementation."""

from __future__ import annotations

from app.design_sync.protocol import (
    DesignComponent,
    DesignFile,
    DesignFileStructure,
    ExportedImage,
    ExtractedTokens,
)


class SketchDesignSyncService:
    """Stub Sketch provider. Returns empty tokens."""

    async def list_files(self, access_token: str) -> list[DesignFile]:
        """Stub — file browsing not supported for Sketch."""
        return []

    async def validate_connection(self, file_ref: str, access_token: str) -> bool:
        """Sketch validation always succeeds (stub)."""
        return True

    async def sync_tokens(self, file_ref: str, access_token: str) -> ExtractedTokens:
        """Sketch sync returns empty tokens (stub)."""
        return ExtractedTokens()

    async def sync_tokens_and_structure(
        self,
        file_ref: str,
        access_token: str,
    ) -> tuple[ExtractedTokens, DesignFileStructure]:
        """Stub — returns empty tokens and structure."""
        return ExtractedTokens(), DesignFileStructure(file_name="")

    async def get_file_structure(
        self,
        file_ref: str,
        access_token: str,
        *,
        depth: int | None = 2,
    ) -> DesignFileStructure:
        """Stub — returns empty file structure."""
        return DesignFileStructure(file_name="")

    async def list_components(
        self,
        file_ref: str,
        access_token: str,
    ) -> list[DesignComponent]:
        """Stub — returns empty component list."""
        return []

    async def export_images(
        self,
        file_ref: str,
        access_token: str,
        node_ids: list[str],
        *,
        format: str = "png",
        scale: float = 2.0,
    ) -> list[ExportedImage]:
        """Stub — returns empty image list."""
        return []
