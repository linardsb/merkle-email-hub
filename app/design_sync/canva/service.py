"""Canva design sync provider — stub implementation."""

from __future__ import annotations

from app.design_sync.protocol import (
    DesignComponent,
    DesignFile,
    DesignFileStructure,
    ExportedImage,
    ExtractedTokens,
)


class CanvaDesignSyncService:
    """Stub Canva provider. Returns empty tokens."""

    async def list_files(self, access_token: str) -> list[DesignFile]:  # noqa: ARG002
        """Stub — file browsing not supported for Canva."""
        return []

    async def validate_connection(self, file_ref: str, access_token: str) -> bool:  # noqa: ARG002
        """Canva validation always succeeds (stub)."""
        return True

    async def sync_tokens(self, file_ref: str, access_token: str) -> ExtractedTokens:  # noqa: ARG002
        """Canva sync returns empty tokens (stub)."""
        return ExtractedTokens()

    async def sync_tokens_and_structure(
        self, file_ref: str, access_token: str  # noqa: ARG002
    ) -> tuple[ExtractedTokens, DesignFileStructure]:
        """Stub — returns empty tokens and structure."""
        return ExtractedTokens(), DesignFileStructure(file_name="")

    async def get_file_structure(
        self,
        file_ref: str,  # noqa: ARG002
        access_token: str,  # noqa: ARG002
        *,
        depth: int | None = 2,  # noqa: ARG002
    ) -> DesignFileStructure:
        """Stub — returns empty file structure."""
        return DesignFileStructure(file_name="")

    async def list_components(
        self,
        file_ref: str,  # noqa: ARG002
        access_token: str,  # noqa: ARG002
    ) -> list[DesignComponent]:
        """Stub — returns empty component list."""
        return []

    async def export_images(
        self,
        file_ref: str,  # noqa: ARG002
        access_token: str,  # noqa: ARG002
        node_ids: list[str],  # noqa: ARG002
        *,
        format: str = "png",  # noqa: ARG002
        scale: float = 2.0,  # noqa: ARG002
    ) -> list[ExportedImage]:
        """Stub — returns empty image list."""
        return []
