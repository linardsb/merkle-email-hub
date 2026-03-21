"""Figma design sync provider — calls the Figma REST API."""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import httpx

from app.core.logging import get_logger
from app.design_sync.exceptions import SyncFailedError
from app.design_sync.protocol import (
    DesignComponent,
    DesignFile,
    DesignFileStructure,
    DesignNode,
    DesignNodeType,
    ExportedImage,
    ExtractedColor,
    ExtractedSpacing,
    ExtractedTokens,
    ExtractedTypography,
)

logger = get_logger(__name__)

_FIGMA_FILE_KEY_RE = re.compile(r"figma\.com/(?:design|file|proto|board|embed)/([a-zA-Z0-9]+)")
_FIGMA_API = "https://api.figma.com"
_TIMEOUT = 30.0
_MAX_WALK_DEPTH = 500

_FIGMA_NODE_TYPE_MAP: dict[str, DesignNodeType] = {
    "DOCUMENT": DesignNodeType.OTHER,
    "CANVAS": DesignNodeType.PAGE,
    "FRAME": DesignNodeType.FRAME,
    "GROUP": DesignNodeType.GROUP,
    "COMPONENT": DesignNodeType.COMPONENT,
    "COMPONENT_SET": DesignNodeType.COMPONENT,
    "INSTANCE": DesignNodeType.INSTANCE,
    "TEXT": DesignNodeType.TEXT,
    "RECTANGLE": DesignNodeType.VECTOR,
    "ELLIPSE": DesignNodeType.VECTOR,
    "LINE": DesignNodeType.VECTOR,
    "VECTOR": DesignNodeType.VECTOR,
    "BOOLEAN_OPERATION": DesignNodeType.VECTOR,
    "STAR": DesignNodeType.VECTOR,
    "REGULAR_POLYGON": DesignNodeType.VECTOR,
}


def extract_file_key(url: str) -> str:
    """Extract the Figma file key from a URL.

    Raises:
        SyncFailedError: If the URL doesn't contain a valid file key.
    """
    m = _FIGMA_FILE_KEY_RE.search(url)
    if not m:
        raise SyncFailedError(
            "Invalid Figma URL. Expected format: figma.com/design/<file_key>/... "
            "(also accepts /file/, /proto/, /board/, /embed/ paths)"
        )
    return m.group(1)


def _rgba_to_hex(r: float, g: float, b: float) -> str:
    """Convert Figma RGBA floats (0-1) to hex string."""
    return f"#{round(r * 255):02X}{round(g * 255):02X}{round(b * 255):02X}"


class FigmaDesignSyncService:
    """Real Figma API integration."""

    async def list_files(self, access_token: str) -> list[DesignFile]:
        """List recent Figma files using GET /v1/me/files/recents."""
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_FIGMA_API}/v1/me/files/recents",
                headers={"X-Figma-Token": access_token},
            )
        if resp.status_code == 403:
            raise SyncFailedError("Figma access denied. Check your Personal Access Token.")
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After", "60")
            raise SyncFailedError(
                f"Figma API rate limit exceeded. Try again in {retry_after} seconds."
            )
        if resp.status_code != 200:
            logger.warning("design_sync.figma.list_files_failed", status=resp.status_code)
            return []

        data: dict[str, Any] = resp.json()
        files: list[DesignFile] = []
        for item in data.get("files", []):
            if not isinstance(item, dict):
                continue
            item_d = cast(dict[str, Any], item)
            file_key = str(item_d.get("key", ""))
            name = str(item_d.get("name", "Untitled"))
            thumbnail = item_d.get("thumbnail_url")
            last_modified_raw = item_d.get("last_modified")
            last_modified: datetime | None = None
            if isinstance(last_modified_raw, str):
                try:
                    last_modified = datetime.fromisoformat(last_modified_raw.replace("Z", "+00:00"))
                except ValueError:
                    pass
            files.append(
                DesignFile(
                    file_id=file_key,
                    name=name,
                    url=f"https://www.figma.com/design/{file_key}",
                    thumbnail_url=str(thumbnail) if thumbnail else None,
                    last_modified=last_modified,
                    folder=str(item_d.get("folder", {}).get("name"))
                    if isinstance(item_d.get("folder"), dict)
                    else None,
                )
            )

        logger.info("design_sync.figma.files_listed", count=len(files))
        return files

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
        if resp.status_code == 429:
            # Rate-limited but token/file may be valid — allow connection creation
            # so the user isn't blocked. Sync will verify access later.
            logger.warning(
                "design_sync.figma.validate_rate_limited",
                file_ref=file_ref,
                retry_after=resp.headers.get("Retry-After", "unknown"),
            )
            return True
        if resp.status_code != 200:
            raise SyncFailedError(f"Figma API error (HTTP {resp.status_code})")
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
            if file_resp.status_code == 429:
                retry_after = file_resp.headers.get("Retry-After", "60")
                raise SyncFailedError(
                    f"Figma API rate limit exceeded. Try again in {retry_after} seconds."
                )
            if file_resp.status_code != 200:
                raise SyncFailedError(f"Figma file API error (HTTP {file_resp.status_code})")

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
        """Extract colour tokens from published styles + node walk fallback."""
        colors: list[ExtractedColor] = []
        seen_hex: set[str] = set()

        # Phase 1: Published styles (better names, take priority)
        raw_styles = file_data.get("styles", {})
        if isinstance(raw_styles, dict):
            styles = cast(dict[str, Any], raw_styles)
            for style_id, style_meta in styles.items():
                if not isinstance(style_meta, dict):
                    continue
                style_meta_d = cast(dict[str, Any], style_meta)
                if style_meta_d.get("styleType") != "FILL":
                    continue
                name = str(style_meta_d.get("name", f"Color-{style_id}"))
                raw_fills = self._find_fills_for_style(file_data, str(style_id))
                # _find_fills_for_style returns [node["fills"]] where fills is a list
                fills_list: list[Any] = raw_fills[0] if raw_fills else []
                if fills_list:
                    fill: Any = fills_list[0]
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
                            seen_hex.add(hex_val)
                            colors.append(ExtractedColor(name=name, hex=hex_val, opacity=opacity))

        # Phase 2: Node walk (picks up unstyled colors, skips duplicates via seen_hex)
        self._walk_for_colors(file_data.get("document", {}), colors, seen_hex)

        return colors

    def _parse_typography(
        self,
        file_data: dict[str, Any],
        styles_data: dict[str, Any],  # noqa: ARG002
    ) -> list[ExtractedTypography]:
        """Extract typography tokens from published styles + node walk fallback."""
        typography: list[ExtractedTypography] = []
        seen_keys: set[tuple[str, str, float]] = set()

        # Phase 1: Published styles (better names, take priority)
        raw_styles = file_data.get("styles", {})
        if isinstance(raw_styles, dict):
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
                    family = str(tp.get("fontFamily", "Unknown"))
                    weight = str(tp.get("fontWeight", "400"))
                    size = float(tp.get("fontSize", 16))
                    seen_keys.add((family, weight, size))
                    typography.append(
                        ExtractedTypography(
                            name=name,
                            family=family,
                            weight=weight,
                            size=size,
                            line_height=float(tp.get("lineHeightPx", 24)),
                        )
                    )

        # Phase 2: Node walk (picks up unstyled typography, skips duplicates via seen_keys)
        self._walk_for_typography(file_data.get("document", {}), typography, seen_keys)

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
        depth: int = 0,
    ) -> None:
        if depth >= _MAX_WALK_DEPTH or not isinstance(node, dict):
            return
        node_d = cast(dict[str, Any], node)
        # Auto-layout frames expose itemSpacing / paddingLeft etc.
        for key in ("itemSpacing", "paddingLeft", "paddingTop"):
            val: Any = node_d.get(key)
            if isinstance(val, (int, float)) and val > 0 and val not in seen:
                seen.add(float(val))
                spacing.append(ExtractedSpacing(name=f"spacing-{int(val)}", value=float(val)))
        for child in cast(list[Any], node_d.get("children", [])):
            self._walk_for_spacing(child, spacing, seen, depth + 1)

    def _walk_for_colors(
        self,
        node: Any,
        colors: list[ExtractedColor],
        seen_hex: set[str],
        depth: int = 0,
    ) -> None:
        """Recursively extract SOLID fill/stroke colors from every node."""
        if depth >= _MAX_WALK_DEPTH or not isinstance(node, dict):
            return
        node_d = cast(dict[str, Any], node)

        for prop in ("fills", "strokes"):
            raw_list = node_d.get(prop)
            if not isinstance(raw_list, list):
                continue
            for fill_item in cast(list[Any], raw_list):  # type: ignore[redundant-cast]
                if not isinstance(fill_item, dict):
                    continue
                fill_d = cast(dict[str, Any], fill_item)
                if fill_d.get("type") != "SOLID":
                    continue
                color_raw = fill_d.get("color")
                if not isinstance(color_raw, dict):
                    continue
                c = cast(dict[str, Any], color_raw)
                alpha = float(c.get("a", 1.0))
                if alpha < 0.01:
                    continue
                hex_val = _rgba_to_hex(
                    float(c.get("r", 0)),
                    float(c.get("g", 0)),
                    float(c.get("b", 0)),
                )
                if hex_val in seen_hex:
                    continue
                seen_hex.add(hex_val)
                colors.append(ExtractedColor(name=hex_val, hex=hex_val, opacity=alpha))

        for child in node_d.get("children", []):
            self._walk_for_colors(child, colors, seen_hex, depth + 1)

    def _walk_for_typography(
        self,
        node: Any,
        typography: list[ExtractedTypography],
        seen_keys: set[tuple[str, str, float]],
        depth: int = 0,
    ) -> None:
        """Recursively extract typography from TEXT nodes."""
        if depth >= _MAX_WALK_DEPTH or not isinstance(node, dict):
            return
        node_d = cast(dict[str, Any], node)

        if str(node_d.get("type", "")) == "TEXT":
            style = node_d.get("style")
            if isinstance(style, dict):
                s = cast(dict[str, Any], style)
                family = str(s.get("fontFamily", ""))
                weight = str(s.get("fontWeight", "400"))
                size = float(s.get("fontSize", 0))
                if family and size > 0:
                    key = (family, weight, size)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        line_height = float(s.get("lineHeightPx", size * 1.2))
                        name = f"{family} {weight} {int(size)}px"
                        typography.append(
                            ExtractedTypography(
                                name=name,
                                family=family,
                                weight=weight,
                                size=size,
                                line_height=line_height,
                            )
                        )

        for child in node_d.get("children", []):
            self._walk_for_typography(child, typography, seen_keys, depth + 1)

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

    # ── Phase 12.1: File Structure, Components, Image Export ──

    async def get_file_structure(
        self, file_ref: str, access_token: str, *, depth: int | None = 2
    ) -> DesignFileStructure:
        """Fetch and parse Figma file structure into a normalised tree."""
        params: dict[str, Any] = {}
        if depth is not None:
            # Figma depth param: 1=pages only, 2=pages+frames, etc.
            # We add 1 because Figma counts from the DOCUMENT root
            params["depth"] = depth + 1

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_FIGMA_API}/v1/files/{file_ref}",
                headers={"X-Figma-Token": access_token},
                params=params,
            )
        if resp.status_code == 403:
            raise SyncFailedError("Figma access denied. Check your Personal Access Token.")
        if resp.status_code == 404:
            raise SyncFailedError("Figma file not found. Check the file URL.")
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After", "60")
            raise SyncFailedError(
                f"Figma API rate limit exceeded. Try again in {retry_after} seconds."
            )
        if resp.status_code != 200:
            raise SyncFailedError(f"Figma API error (HTTP {resp.status_code})")

        data: dict[str, Any] = resp.json()
        file_name = str(data.get("name", "Untitled"))
        document = data.get("document", {})
        pages: list[DesignNode] = []

        max_depth = depth  # None means unlimited
        for page_data in document.get("children", []):
            if isinstance(page_data, dict):
                pages.append(
                    self._parse_node(
                        cast(dict[str, Any], page_data), current_depth=0, max_depth=max_depth
                    )
                )

        logger.info(
            "design_sync.figma.file_structure_fetched",
            file_ref=file_ref,
            pages=len(pages),
        )

        return DesignFileStructure(file_name=file_name, pages=pages)

    def _parse_node(
        self,
        node_data: dict[str, Any],
        current_depth: int,
        max_depth: int | None,
    ) -> DesignNode:
        """Recursively parse a Figma node into a DesignNode."""
        raw_type = str(node_data.get("type", "UNKNOWN"))
        node_type = _FIGMA_NODE_TYPE_MAP.get(raw_type, DesignNodeType.OTHER)

        # Extract dimensions and position from absoluteBoundingBox if present
        bbox = node_data.get("absoluteBoundingBox")
        width: float | None = None
        height: float | None = None
        x: float | None = None
        y: float | None = None
        if isinstance(bbox, dict):
            bbox_d = cast(dict[str, Any], bbox)
            raw_w, raw_h = bbox_d.get("width"), bbox_d.get("height")
            raw_x, raw_y = bbox_d.get("x"), bbox_d.get("y")
            width = float(raw_w) if isinstance(raw_w, (int, float)) else None
            height = float(raw_h) if isinstance(raw_h, (int, float)) else None
            x = float(raw_x) if isinstance(raw_x, (int, float)) else None
            y = float(raw_y) if isinstance(raw_y, (int, float)) else None

        # Extract text content from TEXT nodes
        text_content: str | None = None
        if node_type == DesignNodeType.TEXT:
            raw_chars = node_data.get("characters")
            if isinstance(raw_chars, str) and raw_chars.strip():
                text_content = raw_chars.strip()

        children: list[DesignNode] = []
        # Only recurse if we haven't hit the depth limit
        if max_depth is None or current_depth < max_depth:
            for child_data in node_data.get("children", []):
                if isinstance(child_data, dict):
                    children.append(
                        self._parse_node(
                            cast(dict[str, Any], child_data), current_depth + 1, max_depth
                        )
                    )

        return DesignNode(
            id=str(node_data.get("id", "")),
            name=str(node_data.get("name", "")),
            type=node_type,
            children=children,
            width=width,
            height=height,
            x=x,
            y=y,
            text_content=text_content,
        )

    async def list_components(self, file_ref: str, access_token: str) -> list[DesignComponent]:
        """Fetch published components from a Figma file."""
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_FIGMA_API}/v1/files/{file_ref}/components",
                headers={"X-Figma-Token": access_token},
            )
        if resp.status_code == 403:
            raise SyncFailedError("Figma access denied. Check your Personal Access Token.")
        if resp.status_code == 404:
            raise SyncFailedError("Figma file not found. Check the file URL.")
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After", "60")
            raise SyncFailedError(
                f"Figma API rate limit exceeded. Try again in {retry_after} seconds."
            )
        if resp.status_code != 200:
            raise SyncFailedError(f"Figma components API error (HTTP {resp.status_code})")

        data: dict[str, Any] = resp.json()
        error = data.get("error")
        if error:
            raise SyncFailedError(f"Figma API error: {error}")

        components: list[DesignComponent] = []
        meta = data.get("meta", {})
        raw_components = meta.get("components", [])

        for comp in raw_components:
            if not isinstance(comp, dict):
                continue
            comp_d = cast(dict[str, Any], comp)
            containing_frame = comp_d.get("containing_frame")
            containing_page: str | None = None
            if isinstance(containing_frame, dict):
                raw_page = cast(dict[str, Any], containing_frame).get("pageName")
                containing_page = str(raw_page) if raw_page is not None else None
            thumbnail = comp_d.get("thumbnail_url")
            components.append(
                DesignComponent(
                    component_id=str(comp_d.get("node_id", "")),
                    name=str(comp_d.get("name", "")),
                    description=str(comp_d.get("description", "")),
                    thumbnail_url=str(thumbnail) if thumbnail is not None else None,
                    containing_page=containing_page,
                )
            )

        logger.info(
            "design_sync.figma.components_listed",
            file_ref=file_ref,
            count=len(components),
        )

        return components

    async def export_images(
        self,
        file_ref: str,
        access_token: str,
        node_ids: list[str],
        *,
        format: str = "png",
        scale: float = 2.0,
    ) -> list[ExportedImage]:
        """Export Figma nodes as images, auto-batching in groups of 100."""
        if not node_ids:
            return []

        # Validate format
        valid_formats = {"png", "jpg", "svg", "pdf"}
        if format not in valid_formats:
            raise SyncFailedError(
                f"Invalid export format '{format}'. Valid: {', '.join(sorted(valid_formats))}"
            )

        # Clamp scale to Figma's supported range
        scale = max(0.01, min(scale, 4.0))

        # Batch into groups of 100 (Figma API limit)
        batches: list[list[str]] = [node_ids[i : i + 100] for i in range(0, len(node_ids), 100)]

        headers = {"X-Figma-Token": access_token}
        expires_at = datetime.now(tz=UTC) + timedelta(days=14)
        all_images: list[ExportedImage] = []

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:

            async def _fetch_batch(batch: list[str]) -> dict[str, Any]:
                resp = await client.get(
                    f"{_FIGMA_API}/v1/images/{file_ref}",
                    headers=headers,
                    params={
                        "ids": ",".join(batch),
                        "format": format,
                        "scale": str(scale),
                    },
                )
                if resp.status_code == 403:
                    raise SyncFailedError("Figma access denied.")
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After", "60")
                    raise SyncFailedError(
                        f"Figma API rate limit exceeded. Try again in {retry_after} seconds."
                    )
                if resp.status_code != 200:
                    raise SyncFailedError(f"Figma images API error (HTTP {resp.status_code})")
                result: dict[str, Any] = resp.json()
                return result

            results = await asyncio.gather(*[_fetch_batch(b) for b in batches])

        for result in results:
            images_map = result.get("images", {})
            if not isinstance(images_map, dict):
                continue
            images_map_d = cast(dict[str, Any], images_map)
            for nid, url in images_map_d.items():
                if url is not None:
                    all_images.append(
                        ExportedImage(
                            node_id=str(nid),
                            url=str(url),
                            format=format,
                            expires_at=expires_at,
                        )
                    )

        logger.info(
            "design_sync.figma.images_exported",
            file_ref=file_ref,
            requested=len(node_ids),
            exported=len(all_images),
            format=format,
        )

        return all_images
