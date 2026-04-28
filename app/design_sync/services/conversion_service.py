"""Token reads, diffs, W3C IO, layout analysis, brief generation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from app.core.exceptions import ConflictError
from app.core.logging import get_logger
from app.design_sync.brief_generator import generate_brief as generate_brief_text
from app.design_sync.crypto import decrypt_token
from app.design_sync.exceptions import ConnectionNotFoundError
from app.design_sync.figma.layout_analyzer import (
    analyze_layout as run_layout_analysis,
)
from app.design_sync.protocol import (
    DesignFileStructure,
    ExtractedColor,
    ExtractedSpacing,
    ExtractedTokens,
    ExtractedTypography,
)
from app.design_sync.schemas import (
    CompatibilityHintResponse,
    DesignColorResponse,
    DesignGradientResponse,
    DesignGradientStopResponse,
    DesignSpacingResponse,
    DesignTokensResponse,
    DesignTypographyResponse,
    GenerateBriefResponse,
    LayoutAnalysisResponse,
    TokenDiffEntry,
    TokenDiffResponse,
    W3cImportResponse,
)

if TYPE_CHECKING:
    from app.auth.models import User
    from app.design_sync.schemas import ImportW3cTokensRequest
    from app.design_sync.services._context import DesignSyncContext


logger = get_logger(__name__)


class TokenConversionService:
    """Tokens, diffs, W3C IO, layout analysis, and brief generation."""

    def __init__(self, ctx: DesignSyncContext) -> None:
        self._ctx = ctx

    async def get_diagnostic_data(
        self, connection_id: int, user: User
    ) -> tuple[DesignFileStructure, ExtractedTokens]:
        """Return protocol-level structure + tokens for diagnostic pipeline."""
        from app.design_sync.diagnose.report import _dict_to_tokens, _node_from_dict

        conn = await self._ctx.repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._ctx.verify_access(conn.project_id, user)

        snapshot = await self._ctx.repo.get_latest_snapshot(connection_id)
        if snapshot is None:
            raise ConflictError("No sync snapshot available — sync the connection first")

        tokens_json = snapshot.tokens_json
        cached_structure: dict[str, Any] | None = tokens_json.get("_file_structure")
        if cached_structure is not None:
            raw_pages: list[Any] = cached_structure.get("pages", [])
            pages = [
                _node_from_dict(cast(dict[str, Any], p)) for p in raw_pages if isinstance(p, dict)
            ]
            structure = DesignFileStructure(
                file_name=str(cached_structure.get("file_name", "")),
                pages=pages,
            )
        else:
            structure = DesignFileStructure(file_name="", pages=[])

        tokens = _dict_to_tokens(tokens_json)
        return structure, tokens

    async def get_tokens(self, connection_id: int, user: User) -> DesignTokensResponse:
        """Get the latest design tokens for a connection."""
        conn = await self._ctx.repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._ctx.verify_access(conn.project_id, user)

        snapshot = await self._ctx.repo.get_latest_snapshot(connection_id)
        if snapshot is None:
            return DesignTokensResponse(
                connection_id=connection_id,
                colors=[],
                typography=[],
                spacing=[],
                extracted_at=cast(datetime, conn.created_at),
            )

        tj: dict[str, Any] = snapshot.tokens_json
        colors_list = cast(
            list[dict[str, Any]],
            [c for c in tj.get("colors", []) if isinstance(c, dict)],
        )
        typography_list = cast(
            list[dict[str, Any]],
            [t for t in tj.get("typography", []) if isinstance(t, dict)],
        )
        spacing_list = cast(
            list[dict[str, Any]],
            [s for s in tj.get("spacing", []) if isinstance(s, dict)],
        )
        dark_colors_list = cast(
            list[dict[str, Any]],
            [c for c in tj.get("dark_colors", []) if isinstance(c, dict)],
        )
        gradients_list = cast(
            list[dict[str, Any]],
            [g for g in tj.get("gradients", []) if isinstance(g, dict)],
        )
        raw_warnings_list = cast(
            list[dict[str, Any]],
            [w for w in tj.get("_token_warnings", []) if isinstance(w, dict)],
        )
        warning_strings: list[str] | None = None
        if raw_warnings_list:
            warning_strings = [
                f"[{w.get('level', 'info')}] {w.get('field', '?')}: {w.get('message', '')}"
                for w in raw_warnings_list
            ]

        return DesignTokensResponse(
            connection_id=connection_id,
            colors=[
                DesignColorResponse(
                    name=str(c["name"]),
                    hex=str(c["hex"]),
                    opacity=float(c.get("opacity", 1.0)),
                )
                for c in colors_list
            ],
            typography=[
                DesignTypographyResponse(
                    name=str(t["name"]),
                    family=str(t["family"]),
                    weight=str(t["weight"]),
                    size=float(t["size"]),
                    lineHeight=float(t.get("line_height", t.get("lineHeight", 24))),
                    letterSpacing=t.get("letter_spacing", t.get("letterSpacing")),
                    textTransform=t.get("text_transform", t.get("textTransform")),
                    textDecoration=t.get("text_decoration", t.get("textDecoration")),
                )
                for t in typography_list
            ],
            spacing=[
                DesignSpacingResponse(name=str(s["name"]), value=float(s["value"]))
                for s in spacing_list
            ],
            dark_colors=[
                DesignColorResponse(
                    name=str(c["name"]),
                    hex=str(c["hex"]),
                    opacity=float(c.get("opacity", 1.0)),
                )
                for c in dark_colors_list
            ],
            gradients=[
                DesignGradientResponse(
                    name=str(g["name"]),
                    type=str(g.get("type", "linear")),
                    angle=float(g.get("angle", 180)),
                    stops=[
                        DesignGradientStopResponse(
                            hex=str(s.get("hex", "")),
                            position=float(s.get("position", 0)),
                        )
                        for s in cast(
                            list[dict[str, Any]],
                            [s for s in g.get("stops", []) if isinstance(s, dict)],
                        )
                    ],
                    fallback_hex=str(g.get("fallback_hex", "#808080")),
                )
                for g in gradients_list
            ],
            extracted_at=snapshot.extracted_at,
            warnings=warning_strings or None,
            compatibility_hints=read_compatibility_hints(tj),
        )

    async def get_token_diff(
        self, connection_id: int, user: User | None = None
    ) -> TokenDiffResponse:
        """Compare current token snapshot vs previous."""
        conn = await self._ctx.repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None and user is not None:
            await self._ctx.verify_access(conn.project_id, user)

        current = await self._ctx.repo.get_latest_snapshot(connection_id)
        if current is None:
            return TokenDiffResponse(
                connection_id=connection_id,
                current_extracted_at=cast(datetime, conn.created_at),
                entries=[],
            )

        previous = await self._ctx.repo.get_previous_snapshot(connection_id)
        entries = compute_token_diff(
            current.tokens_json,
            previous.tokens_json if previous else {},
        )

        return TokenDiffResponse(
            connection_id=connection_id,
            current_extracted_at=current.extracted_at,
            previous_extracted_at=previous.extracted_at if previous else None,
            entries=entries,
            has_previous=previous is not None,
        )

    async def import_w3c_tokens(
        self, body: ImportW3cTokensRequest, user: User
    ) -> W3cImportResponse:
        """Parse W3C Design Tokens v1.0 JSON and return validated tokens."""
        from app.design_sync.token_transforms import validate_and_transform
        from app.design_sync.w3c_tokens import parse_w3c_tokens

        result = parse_w3c_tokens(dict(body.tokens_json))

        caniemail_data = None
        if body.target_clients:
            from app.design_sync.caniemail import load_caniemail_data

            caniemail_data = load_caniemail_data()

        tokens, validation_warnings = validate_and_transform(
            result.tokens,
            target_clients=body.target_clients or None,
            caniemail_data=caniemail_data,
        )

        warnings = [w.message for w in result.warnings] + [w.message for w in validation_warnings]

        if body.connection_id is not None:
            conn = await self._ctx.repo.get_connection(body.connection_id)
            if conn is None:
                raise ConnectionNotFoundError(f"Connection {body.connection_id} not found")
            if conn.project_id is not None:
                await self._ctx.verify_access(conn.project_id, user)
            await self._ctx.repo.save_snapshot(body.connection_id, asdict(tokens))

        response = W3cImportResponse(
            colors=[
                DesignColorResponse(name=c.name, hex=c.hex, opacity=c.opacity)
                for c in tokens.colors
            ],
            dark_colors=[
                DesignColorResponse(name=c.name, hex=c.hex, opacity=c.opacity)
                for c in tokens.dark_colors
            ],
            typography=[
                DesignTypographyResponse(
                    name=t.name,
                    family=t.family,
                    weight=t.weight,
                    size=t.size,
                    lineHeight=t.line_height,
                    letterSpacing=t.letter_spacing,
                    textTransform=t.text_transform,
                    textDecoration=t.text_decoration,
                )
                for t in tokens.typography
            ],
            spacing=[DesignSpacingResponse(name=s.name, value=s.value) for s in tokens.spacing],
            gradients=[
                DesignGradientResponse(
                    name=g.name,
                    type=g.type,
                    angle=g.angle,
                    stops=[
                        DesignGradientStopResponse(hex=hex_val, position=pos)
                        for hex_val, pos in g.stops
                    ],
                    fallback_hex=g.fallback_hex,
                )
                for g in tokens.gradients
            ],
            warnings=warnings,
        )

        logger.info(
            "design_sync.w3c_import_completed",
            colors=len(tokens.colors),
            typography=len(tokens.typography),
            spacing=len(tokens.spacing),
            warnings=len(warnings),
            connection_id=body.connection_id,
        )

        return response

    async def export_w3c_tokens(self, connection_id: int, user: User) -> dict[str, object]:
        """Export tokens for a connection in W3C Design Tokens v1.0 format."""
        from app.design_sync.protocol import ExtractedGradient
        from app.design_sync.w3c_export import export_w3c_tokens

        tokens_response = await self.get_tokens(connection_id, user)

        tokens = ExtractedTokens(
            colors=[
                ExtractedColor(name=c.name, hex=c.hex, opacity=c.opacity)
                for c in tokens_response.colors
            ],
            dark_colors=[
                ExtractedColor(name=c.name, hex=c.hex, opacity=c.opacity)
                for c in tokens_response.dark_colors
            ],
            typography=[
                ExtractedTypography(
                    name=t.name,
                    family=t.family,
                    weight=t.weight,
                    size=t.size,
                    line_height=t.lineHeight,
                    letter_spacing=t.letterSpacing,
                    text_transform=t.textTransform,
                    text_decoration=t.textDecoration,
                )
                for t in tokens_response.typography
            ],
            spacing=[ExtractedSpacing(name=s.name, value=s.value) for s in tokens_response.spacing],
            gradients=[
                ExtractedGradient(
                    name=g.name,
                    type=g.type,
                    angle=g.angle,
                    stops=tuple((s.hex, s.position) for s in g.stops),
                    fallback_hex=g.fallback_hex,
                )
                for g in tokens_response.gradients
            ],
        )

        result = export_w3c_tokens(tokens)
        logger.info("design_sync.w3c_export_completed", connection_id=connection_id)
        return result

    async def analyze_layout(
        self,
        connection_id: int,
        user: User,
        *,
        selected_node_ids: list[str] | None = None,
        depth: int | None = 3,
    ) -> LayoutAnalysisResponse:
        """Analyze layout of a design file and return detected sections."""
        from app.design_sync.service import _filter_structure, _layout_to_response
        from app.design_sync.services.assets_service import AssetsService

        conn = await self._ctx.repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._ctx.verify_access(conn.project_id, user)

        provider = self._ctx.get_provider(conn.provider)
        access_token = decrypt_token(conn.encrypted_token)
        # Reuse the cached-structure helper from AssetsService to keep a single
        # cache lookup path; instantiating is cheap (just stores the ctx).
        assets = AssetsService(self._ctx)
        structure = await assets.get_cached_structure(
            conn.id, conn.file_ref, access_token, provider, depth=depth
        )

        if selected_node_ids:
            structure = _filter_structure(structure, selected_node_ids)

        layout = run_layout_analysis(structure)
        return _layout_to_response(connection_id, layout)

    async def generate_brief(
        self,
        connection_id: int,
        user: User,
        *,
        selected_node_ids: list[str] | None = None,
        include_tokens: bool = True,
    ) -> GenerateBriefResponse:
        """Generate a Scaffolder-compatible brief from design analysis."""
        from app.design_sync.service import _filter_structure
        from app.design_sync.services.assets_service import AssetsService

        conn = await self._ctx.repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._ctx.verify_access(conn.project_id, user)

        provider = self._ctx.get_provider(conn.provider)
        access_token = decrypt_token(conn.encrypted_token)
        assets = AssetsService(self._ctx)
        structure = await assets.get_cached_structure(
            conn.id, conn.file_ref, access_token, provider, depth=None
        )

        if selected_node_ids:
            structure = _filter_structure(structure, selected_node_ids)

        layout = run_layout_analysis(structure)

        tokens: ExtractedTokens | None = None
        if include_tokens:
            snapshot = await self._ctx.repo.get_latest_snapshot(connection_id)
            if snapshot is not None:
                try:
                    tokens = ExtractedTokens(
                        colors=[
                            ExtractedColor(**c) for c in snapshot.tokens_json.get("colors", [])
                        ],
                        typography=[
                            ExtractedTypography(**t)
                            for t in snapshot.tokens_json.get("typography", [])
                        ],
                        spacing=[
                            ExtractedSpacing(**s) for s in snapshot.tokens_json.get("spacing", [])
                        ],
                    )
                except Exception:
                    tokens = None
            if tokens is None:
                try:
                    tokens = await provider.sync_tokens(conn.file_ref, access_token)
                except Exception:
                    logger.warning(
                        "design_sync.brief_tokens_skipped",
                        connection_id=connection_id,
                        exc_info=True,
                    )

        brief_text = generate_brief_text(
            layout,
            tokens=tokens,
            asset_url_prefix=f"/api/v1/design-sync/assets/{connection_id}",
            connection_id=connection_id,
        )

        sections_summary = ", ".join(s.section_type.value for s in layout.sections)

        return GenerateBriefResponse(
            connection_id=connection_id,
            brief=brief_text,
            sections_detected=len(layout.sections),
            layout_summary=sections_summary or "no sections detected",
        )


def read_compatibility_hints(
    tj: dict[str, Any],
) -> list[CompatibilityHintResponse] | None:
    """Read stored compatibility hints from snapshot JSON."""
    raw: list[Any] = tj.get("_compatibility_hints", [])
    if not raw:
        return None
    hints = cast(
        list[dict[str, Any]],
        [h for h in raw if isinstance(h, dict)],
    )
    return [
        CompatibilityHintResponse(
            level=str(h.get("level", "info")),
            css_property=str(h.get("css_property", "")),
            message=str(h.get("message", "")),
            affected_clients=list(h.get("affected_clients", [])),
        )
        for h in hints
    ]


def compute_token_diff(current: dict[str, Any], previous: dict[str, Any]) -> list[TokenDiffEntry]:
    """Diff two token snapshot JSON dicts."""
    entries: list[TokenDiffEntry] = []

    diff_specs: list[tuple[str, str, Callable[[dict[str, Any]], tuple[str, ...]]]] = [
        ("color", "colors", lambda c: (c.get("name", ""), c.get("hex", ""))),
        (
            "typography",
            "typography",
            lambda t: (t.get("name", ""), t.get("family", ""), str(t.get("size", ""))),
        ),
        ("spacing", "spacing", lambda s: (s.get("name", ""), str(s.get("value", "")))),
        ("dark_color", "dark_colors", lambda c: (c.get("name", ""), c.get("hex", ""))),
    ]

    for category, json_key, key_fn in diff_specs:
        cur_items = cast(
            list[dict[str, Any]],
            [i for i in current.get(json_key, []) if isinstance(i, dict)],
        )
        prev_items = cast(
            list[dict[str, Any]],
            [i for i in previous.get(json_key, []) if isinstance(i, dict)],
        )

        cur_keys = {key_fn(i): i for i in cur_items}
        prev_keys = {key_fn(i): i for i in prev_items}

        for k in cur_keys:
            if k not in prev_keys:
                entries.append(
                    TokenDiffEntry(
                        category=category,
                        name=cur_keys[k].get("name", "?"),
                        change="added",
                        new_value=str(k),
                    )
                )
        for k in prev_keys:
            if k not in cur_keys:
                entries.append(
                    TokenDiffEntry(
                        category=category,
                        name=prev_keys[k].get("name", "?"),
                        change="removed",
                        old_value=str(k),
                    )
                )

    return entries
