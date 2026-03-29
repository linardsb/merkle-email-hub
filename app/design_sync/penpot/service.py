"""Penpot implementation of DesignSyncProvider protocol."""

from __future__ import annotations

import contextlib
import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.design_sync.exceptions import SyncFailedError
from app.design_sync.penpot.client import PenpotClient
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

if TYPE_CHECKING:
    from app.design_sync.email_design_document import EmailDesignDocument
    from app.design_sync.token_transforms import TokenWarning

logger = get_logger(__name__)

# Penpot URL patterns: penpot.example.com/view/<file-id> or /workspace/<project>/<file>
_PENPOT_URL_RE = re.compile(
    r"(?:view|workspace)/(?:[a-f0-9-]+/)?([a-f0-9-]+)",
)

# Map Penpot node types to protocol DesignNodeType
_PENPOT_NODE_TYPE_MAP: dict[str, DesignNodeType] = {
    "frame": DesignNodeType.FRAME,
    "group": DesignNodeType.GROUP,
    "rect": DesignNodeType.VECTOR,
    "circle": DesignNodeType.VECTOR,
    "path": DesignNodeType.VECTOR,
    "text": DesignNodeType.TEXT,
    "image": DesignNodeType.IMAGE,
    "svg-raw": DesignNodeType.VECTOR,
    "bool": DesignNodeType.VECTOR,
    "component": DesignNodeType.COMPONENT,
}


def _float_or_none(val: object) -> float | None:
    """Convert a value to float if numeric, otherwise None."""
    return float(val) if isinstance(val, (int, float)) else None


def extract_file_id(url: str) -> str:
    """Extract Penpot file UUID from a URL."""
    match = _PENPOT_URL_RE.search(url)
    if match:
        return match.group(1)
    # Fallback: treat as raw file ID (UUID format)
    uuid_match = re.search(r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", url)
    if uuid_match:
        return uuid_match.group(0)
    # Truncate URL in error to avoid leaking tokens in query strings
    safe_url = url[:80] + "..." if len(url) > 80 else url
    raise SyncFailedError(f"Cannot extract Penpot file ID from: {safe_url}")


class PenpotDesignSyncService:
    """Penpot provider for the design sync protocol."""

    def _make_client(self, access_token: str) -> PenpotClient:
        settings = get_settings()
        return PenpotClient(
            base_url=settings.design_sync.penpot_base_url,
            access_token=access_token,
            timeout=settings.design_sync.penpot_request_timeout,
        )

    async def list_files(self, access_token: str) -> list[DesignFile]:
        """List files across all Penpot projects (max 20 projects)."""
        settings = get_settings()
        base_url = settings.design_sync.penpot_base_url
        files: list[DesignFile] = []
        try:
            async with self._make_client(access_token) as client:
                projects = await client.list_projects()
                for project in projects[:20]:
                    project_files = await client.list_project_files(project.id)
                    for pf in project_files:
                        files.append(
                            DesignFile(
                                file_id=pf.id,
                                name=pf.name,
                                url=f"{base_url}/view/{pf.id}",
                                thumbnail_url=None,
                                last_modified=None,
                                folder=project.name,
                            )
                        )
        except Exception:
            logger.warning("design_sync.penpot.list_files_failed", exc_info=True)
            return []
        logger.info("design_sync.penpot.files_listed", count=len(files))
        return files

    async def validate_connection(self, file_ref: str, access_token: str) -> bool:
        async with self._make_client(access_token) as client:
            if not await client.validate():
                raise SyncFailedError("Penpot connection validation failed")
            # Verify file is accessible
            try:
                await client.get_file(file_ref)
            except SyncFailedError:
                raise
            except Exception as exc:
                raise SyncFailedError("Cannot access Penpot file") from exc
        return True

    async def sync_tokens(self, file_ref: str, access_token: str) -> ExtractedTokens:
        tokens, _ = await self.sync_tokens_and_structure(file_ref, access_token)
        return tokens

    async def sync_tokens_and_structure(
        self, file_ref: str, access_token: str
    ) -> tuple[ExtractedTokens, DesignFileStructure]:
        """Extract tokens and structure from a single Penpot API call."""
        async with self._make_client(access_token) as client:
            file_data = await client.get_file(file_ref)
        colors = self._parse_colors(file_data)
        typography = self._parse_typography(file_data)
        spacing = self._parse_spacing(file_data)
        tokens = ExtractedTokens(colors=colors, typography=typography, spacing=spacing)
        file_name = file_data.get("name", "Untitled")
        pages = self._parse_pages(file_data, depth=3)
        structure = DesignFileStructure(file_name=file_name, pages=pages)
        return tokens, structure

    async def build_document(
        self,
        file_ref: str,
        access_token: str,
        *,
        selected_nodes: list[str] | None = None,
        connection_config: dict[str, Any] | None = None,
        target_clients: list[str] | None = None,
    ) -> tuple[EmailDesignDocument, ExtractedTokens, list[TokenWarning], DesignFileStructure]:
        """Build a complete EmailDesignDocument from a Penpot file.

        Encapsulates: API fetch -> token extraction -> validation ->
        tree normalization -> layout analysis -> document assembly.
        """
        from app.design_sync.email_design_document import EmailDesignDocument
        from app.design_sync.figma.tree_normalizer import normalize_tree
        from app.design_sync.token_transforms import (
            validate_and_transform,
        )

        tokens, structure = await self.sync_tokens_and_structure(file_ref, access_token)
        tokens, token_warnings = validate_and_transform(tokens, target_clients=target_clients)
        structure, _stats = normalize_tree(structure)
        document = EmailDesignDocument.from_legacy(
            structure,
            tokens,
            selected_nodes=selected_nodes,
            connection_config=connection_config,
            source_provider="penpot",
            _pre_normalized=True,
        )

        logger.info(
            "design_sync.penpot.build_document_completed",
            file_ref=file_ref,
            sections=len(document.sections),
            token_warnings=len(token_warnings),
        )
        return document, tokens, token_warnings, structure

    async def get_file_structure(
        self,
        file_ref: str,
        access_token: str,
        *,
        depth: int | None = 2,
    ) -> DesignFileStructure:
        async with self._make_client(access_token) as client:
            file_data = await client.get_file(file_ref)
        file_name = file_data.get("name", "Untitled")
        pages = self._parse_pages(file_data, depth=depth)
        return DesignFileStructure(file_name=file_name, pages=pages)

    async def list_components(
        self,
        file_ref: str,
        access_token: str,
    ) -> list[DesignComponent]:
        async with self._make_client(access_token) as client:
            file_data = await client.get_file(file_ref)
        return self._extract_components(file_data)

    async def export_images(
        self,
        file_ref: str,
        access_token: str,
        node_ids: list[str],
        *,
        format: str = "png",
        scale: float = 2.0,  # noqa: ARG002 - required by DesignSyncProvider protocol
    ) -> list[ExportedImage]:
        """Export nodes as images.

        Penpot export API requires page_id, so we find each node's page first.
        Returns placeholder URLs since Penpot export returns raw bytes
        (not URLs like Figma). The asset download service handles saving to disk.
        """
        async with self._make_client(access_token) as client:
            file_data = await client.get_file(file_ref)
        node_page_map = self._build_node_page_map(file_data)

        results: list[ExportedImage] = []
        for nid in node_ids:
            page_id = node_page_map.get(nid)
            if page_id is None:
                logger.warning("penpot.export_node_not_found", node_id=nid)
                continue
            results.append(
                ExportedImage(
                    node_id=nid,
                    url=f"penpot://export/{file_ref}/{page_id}/{nid}.{format}",
                    format=format,
                    expires_at=datetime.now(UTC) + timedelta(days=365),
                ),
            )
        return results

    # ── Internal parsers ──

    def _parse_colors(self, file_data: dict[str, Any]) -> list[ExtractedColor]:
        """Extract shared colors from Penpot file data."""
        colors: list[ExtractedColor] = []
        raw_colors = file_data.get("data", {}).get("colors", {})
        for cid, cdata in raw_colors.items():
            name = cdata.get("name", cid)
            color_hex = cdata.get("color", "")
            opacity = cdata.get("opacity", 1.0)
            if color_hex:
                colors.append(ExtractedColor(name=name, hex=color_hex, opacity=opacity))
        return colors

    def _parse_typography(self, file_data: dict[str, Any]) -> list[ExtractedTypography]:
        """Extract typography styles from Penpot file data."""
        styles: list[ExtractedTypography] = []
        raw_typo = file_data.get("data", {}).get("typographies", {})
        for tid, tdata in raw_typo.items():
            name = tdata.get("name", tid)
            family = tdata.get("font-family", "")
            weight = str(tdata.get("font-weight", "400"))
            size = tdata.get("font-size", 16.0)
            line_height = tdata.get("line-height", 1.5)
            if family:
                styles.append(
                    ExtractedTypography(
                        name=name,
                        family=family,
                        weight=weight,
                        size=float(size),
                        line_height=float(line_height),
                    )
                )
        return styles

    def _parse_spacing(self, file_data: dict[str, Any]) -> list[ExtractedSpacing]:
        """Extract spacing tokens from Penpot layout properties."""
        spacing: list[ExtractedSpacing] = []
        seen: set[str] = set()
        objects = file_data.get("data", {}).get("pages-index", {})
        for page_data in objects.values():
            for obj in page_data.get("objects", {}).values():
                layout = obj.get("layout")
                if layout in ("flex", "grid"):
                    gap = obj.get("layout-gap", {})
                    row_gap = gap.get("row-gap")
                    col_gap = gap.get("column-gap")
                    padding = obj.get("layout-padding", {})
                    for key, val in [("row-gap", row_gap), ("column-gap", col_gap)]:
                        if val is not None:
                            label = f"{key}-{val}"
                            if label not in seen:
                                seen.add(label)
                                spacing.append(ExtractedSpacing(name=key, value=float(val)))
                    for side in ("p1", "p2", "p3", "p4"):
                        pval = padding.get(side)
                        if pval is not None:
                            label = f"padding-{side}-{pval}"
                            if label not in seen:
                                seen.add(label)
                                spacing.append(
                                    ExtractedSpacing(name=f"padding-{side}", value=float(pval))
                                )
        return spacing

    def _parse_pages(self, file_data: dict[str, Any], *, depth: int | None = 2) -> list[DesignNode]:
        """Parse Penpot file data into protocol DesignNode pages."""
        pages: list[DesignNode] = []
        pages_index = file_data.get("data", {}).get("pages-index", {})
        page_order = file_data.get("data", {}).get("pages", [])

        for page_id in page_order:
            page_data = pages_index.get(page_id)
            if page_data is None:
                continue
            objects = page_data.get("objects", {})
            root_id = str(page_id)
            root_obj = objects.get(root_id, {})
            page_name = root_obj.get("name", f"Page {page_id}")

            children: list[DesignNode] = []
            if depth is None or depth > 0:
                child_depth = None if depth is None else depth - 1
                for child_id in root_obj.get("shapes", []):
                    child_obj = objects.get(str(child_id))
                    if child_obj:
                        children.append(
                            self._obj_to_node(str(child_id), child_obj, objects, depth=child_depth),
                        )

            pages.append(
                DesignNode(
                    id=root_id,
                    name=page_name,
                    type=DesignNodeType.PAGE,
                    children=children,
                )
            )
        return pages

    def _obj_to_node(
        self,
        obj_id: str,
        obj: dict[str, Any],
        all_objects: dict[str, Any],
        *,
        depth: int | None,
    ) -> DesignNode:
        """Convert a Penpot object to a protocol DesignNode."""
        node_type_str = obj.get("type", "frame")
        node_type = _PENPOT_NODE_TYPE_MAP.get(node_type_str, DesignNodeType.OTHER)

        # Check if this is a component instance or definition
        if obj.get("component-id"):
            node_type = DesignNodeType.INSTANCE
        if obj.get("component-root"):
            node_type = DesignNodeType.COMPONENT

        # Geometry from selrect (selection rectangle)
        selrect = obj.get("selrect", {})
        x = selrect.get("x")
        y = selrect.get("y")
        width = selrect.get("width")
        height = selrect.get("height")

        # Text content
        text_content: str | None = None
        if node_type_str == "text":
            content = obj.get("content", {})
            paragraphs = content.get("children", []) if isinstance(content, dict) else []
            text_parts: list[str] = []
            for para in paragraphs:
                for span in para.get("children", []):
                    t = span.get("text", "")
                    if t:
                        text_parts.append(t)
            text_content = " ".join(text_parts) if text_parts else None

        # Recurse into children
        children: list[DesignNode] = []
        if depth is None or depth > 0:
            child_depth = None if depth is None else depth - 1
            for child_id in obj.get("shapes", []):
                child_obj = all_objects.get(str(child_id))
                if child_obj:
                    children.append(
                        self._obj_to_node(str(child_id), child_obj, all_objects, depth=child_depth),
                    )

        # Auto-layout spacing
        padding_top = padding_right = padding_bottom = padding_left = None
        item_spacing_val = counter_axis_spacing_val = None
        layout_mode_val: str | None = None
        layout = obj.get("layout")
        if layout in ("flex", "grid"):
            pad = obj.get("layout-padding", {})
            if isinstance(pad, dict):
                padding_top = _float_or_none(pad.get("p1") or pad.get("top"))
                padding_right = _float_or_none(pad.get("p2") or pad.get("right"))
                padding_bottom = _float_or_none(pad.get("p3") or pad.get("bottom"))
                padding_left = _float_or_none(pad.get("p4") or pad.get("left"))
            gap = obj.get("layout-gap", {})
            if isinstance(gap, dict):
                item_spacing_val = _float_or_none(gap.get("row-gap"))
                counter_axis_spacing_val = _float_or_none(gap.get("column-gap"))
            flex_dir = obj.get("layout-flex-dir", "column")
            layout_mode_val = "VERTICAL" if flex_dir == "column" else "HORIZONTAL"

        # TEXT node typography
        dn_font_family: str | None = None
        dn_font_size: float | None = None
        dn_font_weight: int | None = None
        dn_line_height_px: float | None = None
        dn_letter_spacing_px: float | None = None
        if node_type_str == "text":
            content_data = obj.get("content", {})
            paragraphs = content_data.get("children", []) if isinstance(content_data, dict) else []
            for para in paragraphs:
                for span in para.get("children", []):
                    raw_ff = span.get("font-family")
                    if dn_font_family is None and isinstance(raw_ff, str):
                        dn_font_family = raw_ff
                    raw_fs = span.get("font-size")
                    if raw_fs is not None and dn_font_size is None:
                        dn_font_size = float(raw_fs) if isinstance(raw_fs, (int, float)) else None
                    raw_fw = span.get("font-weight")
                    if raw_fw is not None and dn_font_weight is None:
                        with contextlib.suppress(ValueError, TypeError):
                            dn_font_weight = (
                                int(float(raw_fw))
                                if isinstance(raw_fw, (int, float, str))
                                else None
                            )
                    raw_lh = span.get("line-height")
                    if raw_lh is not None and dn_line_height_px is None:
                        dn_line_height_px = (
                            float(raw_lh) if isinstance(raw_lh, (int, float)) else None
                        )

        # Extract fill color for converter pipeline
        fill_color: str | None = None
        text_color_hex: str | None = None
        fills = obj.get("fills", [])
        if isinstance(fills, list):
            for fill in fills:
                if isinstance(fill, dict) and fill.get("fill-color"):
                    hex_val = str(fill["fill-color"])
                    if node_type_str == "text":
                        text_color_hex = hex_val
                    else:
                        fill_color = hex_val
                    break

        return DesignNode(
            id=obj_id,
            name=obj.get("name", ""),
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
            item_spacing=item_spacing_val,
            counter_axis_spacing=counter_axis_spacing_val,
            layout_mode=layout_mode_val,
            font_family=dn_font_family,
            font_size=dn_font_size,
            font_weight=dn_font_weight,
            line_height_px=dn_line_height_px,
            letter_spacing_px=dn_letter_spacing_px,
        )

    def _extract_components(self, file_data: dict[str, Any]) -> list[DesignComponent]:
        """Extract components defined in the Penpot file."""
        components: list[DesignComponent] = []
        raw_components = file_data.get("data", {}).get("components", {})
        for cid, cdata in raw_components.items():
            components.append(
                DesignComponent(
                    component_id=str(cid),
                    name=cdata.get("name", str(cid)),
                    description=cdata.get("annotation", ""),
                    thumbnail_url=None,
                    containing_page=cdata.get("path", ""),
                )
            )
        return components

    def _build_node_page_map(self, file_data: dict[str, Any]) -> dict[str, str]:
        """Build mapping of node_id → page_id for export."""
        node_map: dict[str, str] = {}
        pages_index = file_data.get("data", {}).get("pages-index", {})
        for page_id, page_data in pages_index.items():
            for obj_id in page_data.get("objects", {}):
                node_map[str(obj_id)] = str(page_id)
        return node_map
