"""Figma design sync provider — calls the Figma REST API."""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import httpx

from app.core.config import get_settings
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
    ExtractedVariable,
)

logger = get_logger(__name__)

_FIGMA_FILE_KEY_RE = re.compile(r"figma\.com/(?:design|file|proto|board|embed)/([a-zA-Z0-9]+)")
_FIGMA_API = "https://api.figma.com"
_TIMEOUT = 60.0
_MAX_WALK_DEPTH = 500
_MAX_ALIAS_DEPTH = 10

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


def _rgba_to_hex_with_opacity(
    r: float,
    g: float,
    b: float,
    fill_alpha: float = 1.0,
    node_opacity: float = 1.0,
    bg_hex: str = "#FFFFFF",
) -> str:
    """Convert RGBA + node opacity to composited hex against a background."""
    eff_alpha = fill_alpha * node_opacity
    if eff_alpha >= 0.999:
        return _rgba_to_hex(r, g, b)
    # Parse background hex (fall back to white on malformed input)
    try:
        _bg_r = int(bg_hex[1:3], 16)
        _bg_g = int(bg_hex[3:5], 16)
        _bg_b = int(bg_hex[5:7], 16)
    except (ValueError, IndexError):
        _bg_r, _bg_g, _bg_b = 255, 255, 255
    bg_r = _bg_r / 255.0
    bg_g = _bg_g / 255.0
    bg_b = _bg_b / 255.0
    # Alpha-composite each channel
    final_r = r * eff_alpha + bg_r * (1 - eff_alpha)
    final_g = g * eff_alpha + bg_g * (1 - eff_alpha)
    final_b = b * eff_alpha + bg_b * (1 - eff_alpha)
    return _rgba_to_hex(final_r, final_g, final_b)


def _gradient_midpoint_hex(gradient_stops: list[dict[str, Any]]) -> str | None:
    """Average RGB of first and last gradient stop. Returns None if < 2 stops."""
    if len(gradient_stops) < 2:
        return None
    first = gradient_stops[0].get("color")
    last = gradient_stops[-1].get("color")
    if not isinstance(first, dict) or not isinstance(last, dict):
        return None
    first_d = cast(dict[str, Any], first)
    last_d = cast(dict[str, Any], last)
    avg_r = (float(first_d.get("r", 0)) + float(last_d.get("r", 0))) / 2
    avg_g = (float(first_d.get("g", 0)) + float(last_d.get("g", 0))) / 2
    avg_b = (float(first_d.get("b", 0)) + float(last_d.get("b", 0))) / 2
    return _rgba_to_hex(avg_r, avg_g, avg_b)


def _float_or_none(val: Any) -> float | None:
    """Convert a value to float if numeric, otherwise None."""
    return float(val) if isinstance(val, (int, float)) else None


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
        tokens, _ = await self.sync_tokens_and_structure(file_ref, access_token)
        return tokens

    async def sync_tokens_and_structure(
        self, file_ref: str, access_token: str
    ) -> tuple[ExtractedTokens, DesignFileStructure]:
        """Fetch file once and extract both tokens and structure from the same response."""
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

        settings = get_settings()
        bg_hex = settings.design_sync.opacity_composite_bg

        # Variables-first token extraction
        var_colors: list[ExtractedColor] = []
        var_variables: list[ExtractedVariable] = []
        var_modes: dict[str, str] = {}
        variables_source = False

        if settings.design_sync.figma_variables_enabled:
            try:
                raw_vars = await self._fetch_variables(file_ref, access_token)
                if raw_vars is not None:
                    var_colors, _var_typography, var_variables, var_modes = self._parse_variables(
                        raw_vars, bg_hex=bg_hex
                    )
                    if var_colors:
                        variables_source = True
            except SyncFailedError:
                raise
            except Exception:
                logger.warning("design_sync.figma.variables_parse_failed", exc_info=True)

        # Styles/node-walk fallback (or supplement)
        if variables_source:
            colors = var_colors
            stroke_colors: list[ExtractedColor] = []
        else:
            colors, stroke_colors = self._parse_colors(file_data, styles_data, bg_hex=bg_hex)

        typography = self._parse_typography(file_data, styles_data)
        spacing = self._parse_spacing(file_data)

        logger.info(
            "design_sync.figma.tokens_extracted",
            colors=len(colors),
            typography=len(typography),
            spacing=len(spacing),
            variables_source=variables_source,
        )

        tokens = ExtractedTokens(
            colors=colors,
            typography=typography,
            spacing=spacing,
            variables_source=variables_source,
            modes=var_modes if var_modes else None,
            stroke_colors=stroke_colors if not variables_source else [],
            variables=var_variables,
        )

        # Parse file structure from the same response (no extra API call)
        file_name = str(file_data.get("name", "Untitled"))
        document = file_data.get("document", {})
        pages: list[DesignNode] = []
        for page_data in document.get("children", []):
            if isinstance(page_data, dict):
                pages.append(
                    self._parse_node(cast(dict[str, Any], page_data), current_depth=0, max_depth=3)
                )

        structure = DesignFileStructure(file_name=file_name, pages=pages)

        return tokens, structure

    async def _fetch_variables(self, file_ref: str, access_token: str) -> dict[str, Any] | None:
        """Fetch local and published variables from the Figma Variables API."""
        headers = {"X-Figma-Token": access_token}
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            local_resp = await client.get(
                f"{_FIGMA_API}/v1/files/{file_ref}/variables/local",
                headers=headers,
            )
            if local_resp.status_code == 403:
                logger.info("design_sync.figma.variables_not_available", reason="403")
                return None
            if local_resp.status_code == 429:
                retry_after = local_resp.headers.get("Retry-After", "60")
                raise SyncFailedError(
                    f"Figma API rate limit exceeded. Try again in {retry_after} seconds."
                )
            if local_resp.status_code != 200:
                logger.warning(
                    "design_sync.figma.variables_fetch_failed",
                    status=local_resp.status_code,
                )
                return None

            pub_resp = await client.get(
                f"{_FIGMA_API}/v1/files/{file_ref}/variables/published",
                headers=headers,
            )
            if pub_resp.status_code == 429:
                retry_after = pub_resp.headers.get("Retry-After", "60")
                raise SyncFailedError(
                    f"Figma API rate limit exceeded. Try again in {retry_after} seconds."
                )

        local_json: dict[str, Any] = local_resp.json()
        pub_json: dict[str, Any] = pub_resp.json() if pub_resp.status_code == 200 else {}
        return {"local": local_json, "published": pub_json}

    def _resolve_variable_alias(
        self,
        value: Any,
        variables_by_id: dict[str, dict[str, Any]],
        mode_id: str,
        depth: int = 0,
    ) -> Any:
        """Walk alias chain to resolve a variable value."""
        if depth >= _MAX_ALIAS_DEPTH:
            logger.warning("design_sync.figma.alias_depth_exceeded", depth=depth)
            return None
        if not isinstance(value, dict):
            return value
        value_d = cast(dict[str, Any], value)
        if value_d.get("type") != "VARIABLE_ALIAS":
            return value
        target_id = str(value_d.get("id", ""))
        target_var = variables_by_id.get(target_id)
        if not target_var:
            return None
        values_by_mode = target_var.get("valuesByMode", {})
        resolved = values_by_mode.get(mode_id)
        if resolved is None:
            # Fall back to first available mode
            for v in values_by_mode.values():
                resolved = v
                break
        if resolved is None:
            return None
        return self._resolve_variable_alias(resolved, variables_by_id, mode_id, depth + 1)

    def _parse_variables(
        self, raw: dict[str, Any], bg_hex: str = "#FFFFFF"
    ) -> tuple[
        list[ExtractedColor], list[ExtractedTypography], list[ExtractedVariable], dict[str, str]
    ]:
        """Parse Variables API response into colors, typography (future), variables, and modes."""
        colors: list[ExtractedColor] = []
        seen_hex: set[str] = set()
        variables: list[ExtractedVariable] = []
        global_modes: dict[str, str] = {}

        local_raw = raw.get("local", {})
        local_meta: dict[str, Any] = (
            cast(dict[str, Any], cast(dict[str, Any], local_raw).get("meta", {}))
            if isinstance(local_raw, dict)
            else {}
        )
        meta_d = cast(dict[str, Any], local_meta) if isinstance(local_meta, dict) else {}  # type: ignore[redundant-cast]
        collections: dict[str, Any] = cast(dict[str, Any], meta_d.get("variableCollections", {}))
        all_variables: dict[str, Any] = cast(dict[str, Any], meta_d.get("variables", {}))

        # Build mode name lookup from collections
        mode_name_map: dict[str, str] = {}  # mode_id -> mode_name
        for coll_raw in collections.values():
            if not isinstance(coll_raw, dict):
                continue
            coll_d = cast(dict[str, Any], coll_raw)
            for mode in cast(list[Any], coll_d.get("modes", [])):
                if isinstance(mode, dict):
                    mode_d = cast(dict[str, Any], mode)
                    mid = str(mode_d.get("modeId", ""))
                    mname = str(mode_d.get("name", mid))
                    mode_name_map[mid] = mname

        # Use first collection's modes as global_modes
        for coll_raw in collections.values():
            if isinstance(coll_raw, dict):
                coll_d = cast(dict[str, Any], coll_raw)
                for mode in cast(list[Any], coll_d.get("modes", [])):
                    if isinstance(mode, dict):
                        mode_d = cast(dict[str, Any], mode)
                        mid = str(mode_d.get("modeId", ""))
                        mname = str(mode_d.get("name", mid))
                        global_modes[mname] = mid
                break

        # Default mode: first in global_modes
        default_mode_id = next(iter(global_modes.values()), "")

        for var_id, var_data_raw in all_variables.items():
            if not isinstance(var_data_raw, dict):
                continue
            var_data = cast(dict[str, Any], var_data_raw)
            var_name = str(var_data.get("name", var_id))
            resolved_type = str(var_data.get("resolvedType", ""))
            collection_id = str(var_data.get("variableCollectionId", ""))
            coll_name = ""
            coll_data = collections.get(collection_id)
            if isinstance(coll_data, dict):
                coll_name = str(cast(dict[str, Any], coll_data).get("name", ""))

            values_by_mode_raw: dict[str, Any] = cast(
                dict[str, Any], var_data.get("valuesByMode", {})
            )
            resolved_values: dict[str, Any] = {}
            is_alias = False
            alias_path: str | None = None

            for mid, val in values_by_mode_raw.items():
                mname = mode_name_map.get(mid, mid)
                if (
                    isinstance(val, dict)
                    and cast(dict[str, Any], val).get("type") == "VARIABLE_ALIAS"
                ):
                    is_alias = True
                    target_id_str = str(cast(dict[str, Any], val).get("id", ""))
                    target_var_raw = all_variables.get(target_id_str)
                    if isinstance(target_var_raw, dict):
                        alias_path = str(
                            cast(dict[str, Any], target_var_raw).get("name", target_id_str)
                        )
                resolved = self._resolve_variable_alias(val, all_variables, mid)
                resolved_values[mname] = resolved

            # Strip leading "color/" prefix from display name
            display_name = var_name
            if display_name.lower().startswith("color/"):
                display_name = display_name[6:]

            variables.append(
                ExtractedVariable(
                    name=display_name,
                    collection=coll_name,
                    type=resolved_type,
                    values_by_mode=resolved_values,
                    is_alias=is_alias,
                    alias_path=alias_path,
                )
            )

            # COLOR variables → extract into colors palette
            if resolved_type == "COLOR":
                default_val = self._resolve_variable_alias(
                    values_by_mode_raw.get(default_mode_id), all_variables, default_mode_id
                )
                if isinstance(default_val, dict):
                    dv = cast(dict[str, Any], default_val)
                    r = float(dv.get("r", 0))
                    g = float(dv.get("g", 0))
                    b = float(dv.get("b", 0))
                    a = float(dv.get("a", 1.0))
                    hex_val = _rgba_to_hex_with_opacity(r, g, b, fill_alpha=a, bg_hex=bg_hex)
                    if hex_val not in seen_hex:
                        seen_hex.add(hex_val)
                        colors.append(ExtractedColor(name=display_name, hex=hex_val, opacity=a))

        # Typography from Variables is future work (33.3)
        return colors, [], variables, global_modes

    def _parse_colors(
        self,
        file_data: dict[str, Any],
        styles_data: dict[str, Any],  # noqa: ARG002
        *,
        bg_hex: str = "#FFFFFF",
    ) -> tuple[list[ExtractedColor], list[ExtractedColor]]:
        """Extract colour tokens from published styles + node walk fallback.

        Returns (fill_colors, stroke_colors).
        """
        colors: list[ExtractedColor] = []
        seen_hex: set[str] = set()
        stroke_colors: list[ExtractedColor] = []
        seen_stroke_hex: set[str] = set()

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
                            opacity = float(c.get("a", 1.0))
                            hex_val = _rgba_to_hex_with_opacity(
                                float(c.get("r", 0)),
                                float(c.get("g", 0)),
                                float(c.get("b", 0)),
                                fill_alpha=opacity,
                                bg_hex=bg_hex,
                            )
                            seen_hex.add(hex_val)
                            colors.append(ExtractedColor(name=name, hex=hex_val, opacity=opacity))

        # Phase 2: Node walk (picks up unstyled colors, skips duplicates via seen_hex)
        self._walk_for_colors(
            file_data.get("document", {}),
            colors,
            seen_hex,
            stroke_colors=stroke_colors,
            seen_stroke_hex=seen_stroke_hex,
            bg_hex=bg_hex,
        )

        return colors, stroke_colors

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
        *,
        stroke_colors: list[ExtractedColor] | None = None,
        seen_stroke_hex: set[str] | None = None,
        bg_hex: str = "#FFFFFF",
    ) -> None:
        """Recursively extract fill/stroke colors from every node."""
        if depth >= _MAX_WALK_DEPTH or not isinstance(node, dict):
            return
        node_d = cast(dict[str, Any], node)
        node_opacity = float(node_d.get("opacity", 1.0))
        node_name = str(node_d.get("name", ""))

        if stroke_colors is None:
            stroke_colors = []
        if seen_stroke_hex is None:
            seen_stroke_hex = set()

        # Fills — extract all gradient midpoints, then topmost visible solid
        raw_fills = node_d.get("fills")
        if isinstance(raw_fills, list):
            fills_list = cast(list[Any], raw_fills)  # type: ignore[redundant-cast]
            # Pass 1: gradient midpoints (all of them)
            for fill_item in fills_list:
                if not isinstance(fill_item, dict):
                    continue
                fill_d = cast(dict[str, Any], fill_item)
                if fill_d.get("visible") is False:
                    continue
                if fill_d.get("type") == "GRADIENT_LINEAR":
                    stops = fill_d.get("gradientStops", [])
                    if isinstance(stops, list):
                        midpoint = _gradient_midpoint_hex(cast(list[dict[str, Any]], stops))
                        if midpoint and midpoint not in seen_hex:
                            seen_hex.add(midpoint)
                            gname = f"{node_name} (gradient midpoint)" if node_name else midpoint
                            colors.append(ExtractedColor(name=gname, hex=midpoint, opacity=1.0))

            # Pass 2: topmost visible solid (last in array = topmost in Figma)
            for fill_item in reversed(fills_list):
                if not isinstance(fill_item, dict):
                    continue
                fill_d = cast(dict[str, Any], fill_item)
                if fill_d.get("visible") is False:
                    continue
                if fill_d.get("type") != "SOLID":
                    continue
                color_raw = fill_d.get("color")
                if not isinstance(color_raw, dict):
                    continue
                c = cast(dict[str, Any], color_raw)
                fill_alpha = float(c.get("a", 1.0))
                if fill_alpha * node_opacity < 0.01:
                    continue
                hex_val = _rgba_to_hex_with_opacity(
                    float(c.get("r", 0)),
                    float(c.get("g", 0)),
                    float(c.get("b", 0)),
                    fill_alpha=fill_alpha,
                    node_opacity=node_opacity,
                    bg_hex=bg_hex,
                )
                if hex_val not in seen_hex:
                    seen_hex.add(hex_val)
                    colors.append(ExtractedColor(name=hex_val, hex=hex_val, opacity=fill_alpha))
                break  # Topmost visible solid only

        # Strokes — separate list
        raw_strokes = node_d.get("strokes")
        if isinstance(raw_strokes, list):
            for stroke_item in cast(list[Any], raw_strokes):  # type: ignore[redundant-cast]
                if not isinstance(stroke_item, dict):
                    continue
                stroke_d = cast(dict[str, Any], stroke_item)
                if stroke_d.get("type") != "SOLID":
                    continue
                color_raw = stroke_d.get("color")
                if not isinstance(color_raw, dict):
                    continue
                c = cast(dict[str, Any], color_raw)
                alpha = float(c.get("a", 1.0))
                if alpha < 0.01:
                    continue
                hex_val = _rgba_to_hex_with_opacity(
                    float(c.get("r", 0)),
                    float(c.get("g", 0)),
                    float(c.get("b", 0)),
                    fill_alpha=alpha,
                    node_opacity=node_opacity,
                    bg_hex=bg_hex,
                )
                if hex_val not in seen_stroke_hex:
                    seen_stroke_hex.add(hex_val)
                    stroke_colors.append(ExtractedColor(name=hex_val, hex=hex_val, opacity=alpha))

        for child in node_d.get("children", []):
            self._walk_for_colors(
                child,
                colors,
                seen_hex,
                depth + 1,
                stroke_colors=stroke_colors,
                seen_stroke_hex=seen_stroke_hex,
                bg_hex=bg_hex,
            )

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

        # Auto-layout properties (frames with auto-layout)
        padding_top: float | None = None
        padding_right: float | None = None
        padding_bottom: float | None = None
        padding_left: float | None = None
        item_spacing: float | None = None
        counter_axis_spacing: float | None = None
        layout_mode_str: str | None = None
        if raw_type == "FRAME":
            layout_mode_str = node_data.get("layoutMode")
            if layout_mode_str and layout_mode_str != "NONE":
                padding_top = _float_or_none(node_data.get("paddingTop"))
                padding_right = _float_or_none(node_data.get("paddingRight"))
                padding_bottom = _float_or_none(node_data.get("paddingBottom"))
                padding_left = _float_or_none(node_data.get("paddingLeft"))
                item_spacing = _float_or_none(node_data.get("itemSpacing"))
                counter_axis_spacing = _float_or_none(node_data.get("counterAxisSpacing"))

        # TEXT node typography
        dn_font_family: str | None = None
        dn_font_size: float | None = None
        dn_font_weight: int | None = None
        dn_line_height_px: float | None = None
        dn_letter_spacing_px: float | None = None
        if node_type == DesignNodeType.TEXT:
            style = node_data.get("style", {})
            if isinstance(style, dict):
                raw_ff = style.get("fontFamily")
                dn_font_family = str(raw_ff) if isinstance(raw_ff, str) else None
                raw_fs = style.get("fontSize")
                dn_font_size = float(raw_fs) if isinstance(raw_fs, (int, float)) else None
                raw_fw = style.get("fontWeight")
                dn_font_weight = int(raw_fw) if isinstance(raw_fw, (int, float)) else None
                raw_lh = style.get("lineHeightPx")
                dn_line_height_px = float(raw_lh) if isinstance(raw_lh, (int, float)) else None
                raw_ls = style.get("letterSpacing")
                dn_letter_spacing_px = float(raw_ls) if isinstance(raw_ls, (int, float)) else None

        # Extract fill colors for the converter pipeline
        fill_color: str | None = None
        text_color_hex: str | None = None
        node_opacity = float(node_data.get("opacity", 1.0))
        raw_fills = node_data.get("fills", [])
        if isinstance(raw_fills, list):
            for fill_item in reversed(cast(list[Any], raw_fills)):  # type: ignore[redundant-cast]
                if not isinstance(fill_item, dict):
                    continue
                fi_d = cast(dict[str, Any], fill_item)
                if fi_d.get("visible") is False:
                    continue
                if fi_d.get("type") != "SOLID":
                    continue
                c = fi_d.get("color", {})
                if isinstance(c, dict):
                    c_d = cast(dict[str, Any], c)
                    hex_val = _rgba_to_hex_with_opacity(
                        float(c_d.get("r", 0)),
                        float(c_d.get("g", 0)),
                        float(c_d.get("b", 0)),
                        fill_alpha=float(c_d.get("a", 1.0)),
                        node_opacity=node_opacity,
                    )
                    if node_type == DesignNodeType.TEXT:
                        text_color_hex = hex_val
                    else:
                        fill_color = hex_val
                    break

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
            fill_color=fill_color,
            text_color=text_color_hex,
            padding_top=padding_top,
            padding_right=padding_right,
            padding_bottom=padding_bottom,
            padding_left=padding_left,
            item_spacing=item_spacing,
            counter_axis_spacing=counter_axis_spacing,
            layout_mode=layout_mode_str,
            font_family=dn_font_family,
            font_size=dn_font_size,
            font_weight=dn_font_weight,
            line_height_px=dn_line_height_px,
            letter_spacing_px=dn_letter_spacing_px,
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
