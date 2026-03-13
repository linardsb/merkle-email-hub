"""Figma design sync provider — calls the Figma REST API."""

from __future__ import annotations

import re
from typing import Any, cast

import httpx

from app.core.logging import get_logger
from app.design_sync.exceptions import SyncFailedError
from app.design_sync.protocol import (
    ExtractedColor,
    ExtractedSpacing,
    ExtractedTokens,
    ExtractedTypography,
)

logger = get_logger(__name__)

_FIGMA_FILE_KEY_RE = re.compile(r"figma\.com/(?:design|file)/([a-zA-Z0-9]+)")
_FIGMA_API = "https://api.figma.com"
_TIMEOUT = 30.0


def extract_file_key(url: str) -> str:
    """Extract the Figma file key from a URL.

    Raises:
        SyncFailedError: If the URL doesn't contain a valid file key.
    """
    m = _FIGMA_FILE_KEY_RE.search(url)
    if not m:
        raise SyncFailedError("Invalid Figma URL. Expected format: figma.com/design/<file_key>/...")
    return m.group(1)


def _rgba_to_hex(r: float, g: float, b: float) -> str:
    """Convert Figma RGBA floats (0-1) to hex string."""
    return f"#{round(r * 255):02X}{round(g * 255):02X}{round(b * 255):02X}"


class FigmaDesignSyncService:
    """Real Figma API integration."""

    async def validate_connection(self, file_ref: str, access_token: str) -> bool:
        """Check that the PAT can access the file."""
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_FIGMA_API}/v1/files/{file_ref}",
                headers={"X-Figma-Token": access_token},
                params={"depth": 1},
            )
        if resp.status_code == 403:
            raise SyncFailedError("Figma access denied. Check your Personal Access Token.")
        if resp.status_code == 404:
            raise SyncFailedError("Figma file not found. Check the file URL.")
        if resp.status_code != 200:
            raise SyncFailedError(f"Figma API returned status {resp.status_code}")
        return True

    async def sync_tokens(self, file_ref: str, access_token: str) -> ExtractedTokens:
        """Fetch styles from Figma and parse into design tokens."""
        headers = {"X-Figma-Token": access_token}

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # Fetch file for document tree (auto-layout spacing)
            file_resp = await client.get(
                f"{_FIGMA_API}/v1/files/{file_ref}",
                headers=headers,
            )
            if file_resp.status_code != 200:
                raise SyncFailedError(f"Figma file API returned {file_resp.status_code}")

            # Fetch published styles
            styles_resp = await client.get(
                f"{_FIGMA_API}/v1/files/{file_ref}/styles",
                headers=headers,
            )

        file_data: dict[str, Any] = file_resp.json()
        styles_data: dict[str, Any] = styles_resp.json() if styles_resp.status_code == 200 else {}

        colors = self._parse_colors(file_data, styles_data)
        typography = self._parse_typography(file_data, styles_data)
        spacing = self._parse_spacing(file_data)

        logger.info(
            "design_sync.figma.tokens_extracted",
            colors=len(colors),
            typography=len(typography),
            spacing=len(spacing),
        )

        return ExtractedTokens(colors=colors, typography=typography, spacing=spacing)

    def _parse_colors(
        self,
        file_data: dict[str, Any],
        styles_data: dict[str, Any],  # noqa: ARG002
    ) -> list[ExtractedColor]:
        """Extract colour tokens from styles metadata."""
        colors: list[ExtractedColor] = []
        raw_styles = file_data.get("styles", {})
        if not isinstance(raw_styles, dict):
            return colors
        styles = cast(dict[str, Any], raw_styles)

        for style_id, style_meta in styles.items():
            if not isinstance(style_meta, dict):
                continue
            style_meta_d = cast(dict[str, Any], style_meta)
            if style_meta_d.get("styleType") != "FILL":
                continue
            name = str(style_meta_d.get("name", f"Color-{style_id}"))
            # Try to find colour from style node
            fills = self._find_fills_for_style(file_data, str(style_id))
            if fills:
                fill = fills[0]
                if isinstance(fill, dict) and "color" in fill:
                    fill_d = cast(dict[str, Any], fill)
                    color_raw = fill_d["color"]
                    if isinstance(color_raw, dict):
                        c = cast(dict[str, Any], color_raw)
                        hex_val = _rgba_to_hex(
                            float(c.get("r", 0)),
                            float(c.get("g", 0)),
                            float(c.get("b", 0)),
                        )
                        opacity = float(c.get("a", 1.0))
                        colors.append(ExtractedColor(name=name, hex=hex_val, opacity=opacity))
        return colors

    def _parse_typography(
        self,
        file_data: dict[str, Any],
        styles_data: dict[str, Any],  # noqa: ARG002
    ) -> list[ExtractedTypography]:
        """Extract typography tokens from styles metadata."""
        typography: list[ExtractedTypography] = []
        raw_styles = file_data.get("styles", {})
        if not isinstance(raw_styles, dict):
            return typography
        styles = cast(dict[str, Any], raw_styles)

        for style_id, style_meta in styles.items():
            if not isinstance(style_meta, dict):
                continue
            style_meta_d = cast(dict[str, Any], style_meta)
            if style_meta_d.get("styleType") != "TEXT":
                continue
            name = str(style_meta_d.get("name", f"Type-{style_id}"))
            type_props = self._find_type_style_for_style(file_data, str(style_id))
            if type_props and isinstance(type_props, dict):
                tp = cast(dict[str, Any], type_props)
                typography.append(
                    ExtractedTypography(
                        name=name,
                        family=str(tp.get("fontFamily", "Unknown")),
                        weight=str(tp.get("fontWeight", "400")),
                        size=float(tp.get("fontSize", 16)),
                        line_height=float(tp.get("lineHeightPx", 24)),
                    )
                )
        return typography

    def _parse_spacing(self, file_data: dict[str, Any]) -> list[ExtractedSpacing]:
        """Extract spacing from auto-layout frames in the document tree."""
        spacing: list[ExtractedSpacing] = []
        seen: set[float] = set()
        self._walk_for_spacing(file_data.get("document", {}), spacing, seen)
        return sorted(spacing, key=lambda s: s.value)

    def _walk_for_spacing(
        self,
        node: Any,
        spacing: list[ExtractedSpacing],
        seen: set[float],
    ) -> None:
        if not isinstance(node, dict):
            return
        node_d = cast(dict[str, Any], node)
        # Auto-layout frames expose itemSpacing / paddingLeft etc.
        for key in ("itemSpacing", "paddingLeft", "paddingTop"):
            val: Any = node_d.get(key)
            if isinstance(val, (int, float)) and val > 0 and val not in seen:
                seen.add(float(val))
                spacing.append(ExtractedSpacing(name=f"spacing-{int(val)}", value=float(val)))
        for child in cast(list[Any], node_d.get("children", [])):
            self._walk_for_spacing(child, spacing, seen)

    def _find_fills_for_style(self, file_data: dict[str, Any], style_id: str) -> list[Any]:
        """Walk document tree looking for a node that references this style."""
        return self._walk_for_style_property(file_data.get("document", {}), style_id, "fills")

    def _find_type_style_for_style(self, file_data: dict[str, Any], style_id: str) -> Any:
        """Walk document tree looking for a node with this text style."""
        results = self._walk_for_style_property(file_data.get("document", {}), style_id, "style")
        return results[0] if results else None

    def _walk_for_style_property(self, node: Any, style_id: str, prop: str) -> list[Any]:
        """Recursively search for a node referencing the given style ID."""
        if not isinstance(node, dict):
            return []
        node_d = cast(dict[str, Any], node)
        node_styles = node_d.get("styles", {})
        if isinstance(node_styles, dict):
            node_styles_d = cast(dict[str, Any], node_styles)
            for _key, sid in node_styles_d.items():
                if str(sid) == style_id and prop in node_d:
                    return [node_d[prop]]
        results: list[Any] = []
        for child in cast(list[Any], node_d.get("children", [])):
            results.extend(self._walk_for_style_property(child, style_id, prop))
            if results:
                return results
        return results
