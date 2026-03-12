"""Protocol interface for design tool sync implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
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

    colors: list[ExtractedColor] = field(default_factory=list)
    typography: list[ExtractedTypography] = field(default_factory=list)
    spacing: list[ExtractedSpacing] = field(default_factory=list)


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
