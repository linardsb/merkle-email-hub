"""Protocol interface for design tool sync implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ExtractedColor:
    """A colour extracted from a design file."""

    name: str
    hex: str
    opacity: float = 1.0


@dataclass(frozen=True)
class ExtractedTypography:
    """A typography style extracted from a design file."""

    name: str
    family: str
    weight: str
    size: float
    line_height: float


@dataclass(frozen=True)
class ExtractedSpacing:
    """A spacing value extracted from a design file."""

    name: str
    value: float


@dataclass(frozen=True)
class ExtractedTokens:
    """All design tokens extracted from a design file."""

    colors: list[ExtractedColor] = field(default_factory=list[ExtractedColor])
    typography: list[ExtractedTypography] = field(default_factory=list[ExtractedTypography])
    spacing: list[ExtractedSpacing] = field(default_factory=list[ExtractedSpacing])


class DesignNodeType(StrEnum):
    """Normalised node types across design tools."""

    PAGE = "PAGE"
    FRAME = "FRAME"
    COMPONENT = "COMPONENT"
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    GROUP = "GROUP"
    INSTANCE = "INSTANCE"
    VECTOR = "VECTOR"
    OTHER = "OTHER"


@dataclass(frozen=True)
class DesignNode:
    """A node in the design file tree."""

    id: str
    name: str
    type: DesignNodeType
    children: list[DesignNode] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]
    width: float | None = None
    height: float | None = None
    x: float | None = None
    y: float | None = None
    text_content: str | None = None


@dataclass(frozen=True)
class DesignFileStructure:
    """Top-level structure of a design file."""

    file_name: str
    pages: list[DesignNode] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]


@dataclass(frozen=True)
class DesignComponent:
    """A reusable component from a design file."""

    component_id: str
    name: str
    description: str = ""
    thumbnail_url: str | None = None
    containing_page: str | None = None


@dataclass(frozen=True)
class ExportedImage:
    """An exported image from a design file node."""

    node_id: str
    url: str
    format: str  # "png", "jpg", "svg", "pdf"
    expires_at: datetime | None = None


@runtime_checkable
class DesignSyncProvider(Protocol):
    """Protocol that all design tool sync services must implement."""

    async def validate_connection(self, file_ref: str, access_token: str) -> bool:
        """Validate that credentials can access the design file.

        Args:
            file_ref: Provider-specific file reference (e.g. Figma file key).
            access_token: Provider-specific access token or PAT.

        Returns:
            True if the connection is valid.

        Raises:
            SyncFailedError: If validation fails.
        """
        ...

    async def sync_tokens(self, file_ref: str, access_token: str) -> ExtractedTokens:
        """Extract design tokens from a design file.

        Args:
            file_ref: Provider-specific file reference.
            access_token: Provider-specific access token.

        Returns:
            Extracted design tokens (colors, typography, spacing).

        Raises:
            SyncFailedError: If extraction fails.
        """
        ...

    async def get_file_structure(
        self, file_ref: str, access_token: str, *, depth: int | None = 2
    ) -> DesignFileStructure:
        """Get the hierarchical structure of a design file.

        Args:
            file_ref: Provider-specific file reference.
            access_token: Provider-specific access token.
            depth: Max tree depth (None = unlimited, default 2 = pages + top-level frames).

        Returns:
            File structure with pages and nested nodes.

        Raises:
            SyncFailedError: If retrieval fails.
        """
        ...

    async def list_components(self, file_ref: str, access_token: str) -> list[DesignComponent]:
        """List reusable components defined in a design file.

        Args:
            file_ref: Provider-specific file reference.
            access_token: Provider-specific access token.

        Returns:
            List of components with metadata.

        Raises:
            SyncFailedError: If retrieval fails.
        """
        ...

    async def export_images(
        self,
        file_ref: str,
        access_token: str,
        node_ids: list[str],
        *,
        format: str = "png",
        scale: float = 2.0,
    ) -> list[ExportedImage]:
        """Export design nodes as images.

        Args:
            file_ref: Provider-specific file reference.
            access_token: Provider-specific access token.
            node_ids: IDs of nodes to export.
            format: Image format (png, jpg, svg, pdf).
            scale: Export scale factor (1.0-4.0).

        Returns:
            List of exported images with temporary download URLs.

        Raises:
            SyncFailedError: If export fails.
        """
        ...
