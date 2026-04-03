"""Service layer for design-to-email HTML conversion (provider-agnostic)."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.design_sync.compatibility import CompatibilityHint, ConverterCompatibility
from app.design_sync.converter import (
    _has_visible_content,
    _NodeProps,
    _sanitize_css_value,
    convert_colors_to_palette,
    convert_typography,
    node_to_email_html,
)
from app.design_sync.exceptions import MjmlCompileError
from app.design_sync.figma.layout_analyzer import (
    DesignLayoutDescription,
    EmailSection,
    EmailSectionType,
    TextBlock,
)
from app.design_sync.figma.tree_normalizer import normalize_tree
from app.design_sync.html_formatter import format_email_html
from app.design_sync.mjml_template_engine import (
    build_template_context,
    get_engine,
    inject_section_markers,
)
from app.design_sync.protocol import (
    DesignFileStructure,
    DesignNode,
    DesignNodeType,
    ExtractedColor,
    ExtractedGradient,
    ExtractedTokens,
)
from app.design_sync.quality_contracts import QualityWarning, run_quality_contracts

if TYPE_CHECKING:
    from app.design_sync.email_design_document import EmailDesignDocument
    from app.design_sync.vlm_classifier import VLMSectionClassification

logger = get_logger(__name__)


EMAIL_SKELETON = """<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="format-detection" content="telephone=no,date=no,address=no,email=no,url=no">
<meta name="x-apple-disable-message-reformatting">
<!--[if mso]>
<noscript><xml>
<o:OfficeDocumentSettings>
<o:PixelsPerInch>96</o:PixelsPerInch>
</o:OfficeDocumentSettings>
</xml></noscript>
<![endif]-->
{style_block}
</head>
<body role="article" aria-roledescription="email" lang="en" style="margin:0;padding:0;word-spacing:normal;background-color:{bg_color};color:{text_color};font-family:{body_font};text-size-adjust:100%;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">
<!--[if mso]>
<table role="presentation" width="{container_width}" align="center" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;"><tr><td>
<![endif]-->
<table role="presentation" width="{container_width}" style="margin:0 auto;max-width:{container_width}px;width:100%;border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;" cellpadding="0" cellspacing="0" border="0">
{sections}
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->
</body>
</html>"""


# Component-based shell: sections are independent table blocks inside a div,
# NOT <tr> rows in one <table>. Matches the email-shell component pattern.
COMPONENT_SHELL = """\
<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="x-apple-disable-message-reformatting">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="format-detection" content="telephone=no,date=no,address=no,email=no,url=no">
{meta_tags}
<!--[if mso]>
<noscript><xml>
<o:OfficeDocumentSettings>
<o:PixelsPerInch>96</o:PixelsPerInch>
</o:OfficeDocumentSettings>
</xml></noscript>
<style>
td,th,div,p,a,h1,h2,h3,h4,h5,h6 {{font-family: {mso_font}; mso-line-height-rule: exactly;}}
</style>
<![endif]-->
{style_block}
</head>
<body role="article" aria-roledescription="email" lang="en" style="margin:0;padding:0;width:100%;-webkit-text-size-adjust:100%;background-color:{bg_color};font-family:{body_font};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;">
<tr>
<td align="center" style="font-size:{base_size};font-family:{body_font};">
<!--[if mso]>
<table role="presentation" cellpadding="0" cellspacing="0" width="{container_width}" align="center" style="border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;"><tr><td>
<![endif]-->
<table class="dark-bg" role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:{container_width}px;border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;background-color:{bg_color};">
<tr>
<td>
{sections}
</td>
</tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->
</td>
</tr>
</table>
</body>
</html>"""


@dataclass(frozen=True)
class ConversionResult:
    """Result of converting a design tree to email HTML."""

    html: str
    sections_count: int
    warnings: list[str] = field(default_factory=list)
    layout: DesignLayoutDescription | None = None
    compatibility_hints: list[CompatibilityHint] = field(default_factory=list)
    images: list[dict[str, str]] = field(default_factory=list)
    cache_hit_rate: float | None = None
    quality_warnings: list[QualityWarning] = field(default_factory=list)
    match_confidences: dict[int, float] = field(default_factory=dict)
    figma_url: str | None = None
    node_id: str | None = None
    design_tokens_used: dict[str, Any] | None = None
    # VLM verification loop metadata (Phase 47.5)
    verification_iterations: int = 0
    verification_initial_fidelity: float | None = None
    verification_final_fidelity: float | None = None


@dataclass(frozen=True)
class MjmlError:
    """Single MJML validation error returned by the sidecar."""

    line: int
    message: str
    tag_name: str


@dataclass(frozen=True)
class MjmlCompileResult:
    """Result of MJML compilation via the Maizzle sidecar."""

    html: str
    errors: list[MjmlError]
    build_time_ms: float
    optimization: dict[str, Any] | None = None


# Backward-compatible alias
PenpotConversionResult = ConversionResult

_DARK_MODE_CLASS_PREFIX = "dm-"


def dark_mode_style_block(
    light_colors: list[ExtractedColor],
    dark_colors: list[ExtractedColor],
) -> str:
    """Generate 3-tier dark mode CSS block.

    Tier 1: meta tags (injected in skeleton <head>)
    Tier 2: @media (prefers-color-scheme: dark) with !important
    Tier 3: [data-ogsc]/[data-ogsb] for Outlook.com
    """
    if not dark_colors:
        return ""

    # Build light→dark mapping by name, sanitize hex for CSS context
    dark_by_name = {c.name.lower(): c for c in dark_colors}
    pairs: list[tuple[str, str]] = []  # (light_name_lower, sanitized_dark_hex)
    for light in light_colors:
        dark = dark_by_name.get(light.name.lower())
        if dark:
            safe_hex = _sanitize_css_value(dark.hex) or dark.hex
            pairs.append((light.name.lower(), safe_hex))

    if not pairs:
        return ""

    lines = ["<style>"]

    # Tier 2: @media prefers-color-scheme
    lines.append("  @media (prefers-color-scheme: dark) {")
    lines.append(f"    body {{ background-color:{pairs[0][1]} !important; }}")
    for i, (name, dark_hex) in enumerate(pairs):
        cls = f"{_DARK_MODE_CLASS_PREFIX}{i}"
        # Background swap
        lines.append(f"    .{cls} {{ background-color:{dark_hex} !important; }}")
        # Text color swap (if it's a text-role color)
        if any(kw in name for kw in ("text", "body", "foreground")):
            lines.append(f"    .{cls}-text {{ color:{dark_hex} !important; }}")
    lines.append("  }")

    # Tier 3: Outlook.com [data-ogsc] (text) / [data-ogsb] (background)
    for i, (name, dark_hex) in enumerate(pairs):
        cls = f"{_DARK_MODE_CLASS_PREFIX}{i}"
        lines.append(f"  [data-ogsb] .{cls} {{ background-color:{dark_hex} !important; }}")
        if any(kw in name for kw in ("text", "body", "foreground")):
            lines.append(f"  [data-ogsc] .{cls}-text {{ color:{dark_hex} !important; }}")
    lines.append("</style>")
    return "\n".join(lines)


def dark_mode_meta_tags() -> str:
    """Return required dark mode meta tags for <head>."""
    return (
        '<meta name="color-scheme" content="light dark">\n'
        '<meta name="supported-color-schemes" content="light dark">'
    )


class DesignConverterService:
    """Orchestrates design tree → email HTML conversion (provider-agnostic)."""

    # ── Document-based entry points (Phase 36.2) ──────────────────────

    def convert_document(
        self,
        document: EmailDesignDocument,
        *,
        target_clients: list[str] | None = None,
        use_components: bool = True,
        image_urls: dict[str, str] | None = None,
        connection_id: str | None = None,
        design_screenshots: dict[str, bytes] | None = None,
    ) -> ConversionResult:
        """Convert an EmailDesignDocument into email HTML.

        Primary entry point for Phase 36+.  The document already contains
        pre-analysed layout and validated tokens, so no tree normalisation
        or layout analysis is performed here.

        Args:
            document: Pre-validated EmailDesignDocument.
            target_clients: Target email clients for compatibility checks.
            use_components: Use component-template rendering if sections exist.
            image_urls: Mapping of node-id → image URL for component matcher.
            connection_id: If set and caching enabled, cache section results.
            design_screenshots: Figma PNG bytes per node-id (async verification only).
        """
        # design_screenshots is accepted but not used in this sync method;
        # callers can pass it through to async verification separately.
        _ = design_screenshots
        from app.design_sync.token_transforms import validate_and_transform

        tokens = document.to_extracted_tokens()
        tokens, token_warnings = validate_and_transform(tokens, target_clients=target_clients)

        warnings: list[str] = [w.message for w in token_warnings]
        layout = document.to_layout_description()
        container_width = document.layout.container_width
        compat = ConverterCompatibility(target_clients=target_clients)

        if not layout.sections:
            logger.warning("design_sync.convert_document_no_sections")
            return ConversionResult(html="", sections_count=0, warnings=["No sections found"])

        # Compute section hashes for caching (sync/memory-only path)
        section_hashes: dict[str, str] | None = None
        if connection_id and get_settings().design_sync.section_cache_enabled:
            from app.design_sync.section_cache import compute_section_hash

            section_hashes = {
                s.node_id: compute_section_hash(
                    s, tokens, container_width=container_width, target_clients=target_clients
                )
                for s in layout.sections
            }

        if use_components:
            return self._convert_with_components(
                _frames=[],
                layout=layout,
                tokens=tokens,
                warnings=warnings,
                compat=compat,
                container_width=container_width,
                image_urls=image_urls,
                connection_id=connection_id,
                section_hashes=section_hashes,
            )

        # Recursive converter requires full DesignNode frames which the
        # document path doesn't carry.  Fall back to an empty result.
        logger.warning("design_sync.convert_document_no_recursive_fallback")
        return ConversionResult(
            html="",
            sections_count=0,
            warnings=[*warnings, "Recursive converter not available in document path"],
        )

    async def convert_document_mjml(
        self,
        document: EmailDesignDocument,
        *,
        target_clients: list[str] | None = None,
        connection_id: str | None = None,
        design_screenshots: dict[str, bytes] | None = None,
    ) -> ConversionResult:
        """Convert an EmailDesignDocument into email HTML via MJML.

        Generates MJML markup from the document's layout, compiles via
        the Maizzle sidecar.  Unlike ``convert_mjml()``, this does NOT
        fall back to the recursive converter on compilation failure —
        callers should use ``convert_mjml()`` (the shim) if they need
        that fallback.
        """
        from app.design_sync.token_transforms import validate_and_transform

        tokens = document.to_extracted_tokens()
        tokens, token_warnings = validate_and_transform(tokens, target_clients=target_clients)

        warnings: list[str] = [w.message for w in token_warnings]
        layout = document.to_layout_description()
        container_width = document.layout.container_width

        if not layout.sections:
            logger.warning("design_sync.convert_document_mjml_no_sections")
            return ConversionResult(html="", sections_count=0, warnings=["No sections found"])

        result = await self._convert_mjml_from_layout(
            layout=layout,
            tokens=tokens,
            warnings=warnings,
            container_width=container_width,
            target_clients=target_clients,
            connection_id=connection_id,
        )
        return await self._apply_verification(
            result, design_screenshots or {}, layout.sections, container_width
        )

    # ── VLM verification loop (Phase 47.5) ────────────────────────────

    async def _apply_verification(
        self,
        result: ConversionResult,
        design_screenshots: dict[str, bytes],
        sections: list[EmailSection],
        container_width: int,
    ) -> ConversionResult:
        """Run VLM verification loop on conversion result if enabled."""
        ds = get_settings().design_sync
        if not ds.vlm_verify_enabled or not design_screenshots:
            return result

        from app.design_sync.visual_verify import run_verification_loop

        try:
            vr = await run_verification_loop(
                html=result.html,
                design_screenshots=design_screenshots,
                sections=sections,
                max_iterations=ds.vlm_verify_max_iterations,
                render_client=ds.vlm_verify_client,
                viewport_width=container_width,
            )
        except Exception:
            logger.warning("design_sync.verification_loop_failed", exc_info=True)
            return result

        return ConversionResult(
            html=vr.final_html,
            sections_count=result.sections_count,
            warnings=result.warnings,
            layout=result.layout,
            compatibility_hints=result.compatibility_hints,
            images=result.images,
            cache_hit_rate=result.cache_hit_rate,
            quality_warnings=result.quality_warnings,
            match_confidences=result.match_confidences,
            figma_url=result.figma_url,
            node_id=result.node_id,
            design_tokens_used=result.design_tokens_used,
            verification_iterations=len(vr.iterations),
            verification_initial_fidelity=vr.initial_fidelity,
            verification_final_fidelity=vr.final_fidelity,
        )

    # ── Legacy entry points (shim to document path) ──────────────────

    def convert(
        self,
        structure: DesignFileStructure,
        tokens: ExtractedTokens,
        *,
        raw_file_data: dict[str, Any] | None = None,
        selected_nodes: list[str] | None = None,
        target_clients: list[str] | None = None,
        use_components: bool = True,
        connection_config: dict[str, Any] | None = None,
        image_urls: dict[str, str] | None = None,
        connection_id: str | None = None,
        vlm_classifications: dict[str, VLMSectionClassification] | None = None,
    ) -> ConversionResult:
        """Convert a design file structure into an email HTML skeleton.

        Shim: builds an ``EmailDesignDocument`` via ``from_legacy()`` and
        delegates to ``convert_document()``.  Falls back to the legacy
        recursive converter when ``use_components`` is False (requires
        the full DesignNode tree which the document path doesn't carry).
        """
        from app.design_sync.email_design_document import EmailDesignDocument

        # Normalize once — reused by both from_legacy and recursive fallback
        structure, _norm_stats = normalize_tree(structure, raw_file_data=raw_file_data)

        document = EmailDesignDocument.from_legacy(
            structure,
            tokens,
            selected_nodes=selected_nodes,
            connection_config=connection_config,
            _pre_normalized=True,
            vlm_classifications=vlm_classifications,
        )

        if use_components:
            return self.convert_document(
                document,
                target_clients=target_clients,
                use_components=True,
                image_urls=image_urls,
                connection_id=connection_id,
            )

        # Recursive converter requires full DesignNode frames
        frames = self._collect_frames(structure, selected_nodes)
        if not frames:
            logger.warning("design_sync.converter_no_frames")
            return ConversionResult(html="", sections_count=0, warnings=["No frames found"])

        layout = document.to_layout_description()
        container_width = document.layout.container_width
        compat = ConverterCompatibility(target_clients=target_clients)

        return self._convert_recursive(
            frames=frames,
            layout=layout,
            tokens=document.to_extracted_tokens(),
            warnings=[],
            compat=compat,
            container_width=container_width,
            raw_file_data=raw_file_data,
        )

    async def convert_mjml(
        self,
        structure: DesignFileStructure,
        tokens: ExtractedTokens,
        *,
        raw_file_data: dict[str, Any] | None = None,
        selected_nodes: list[str] | None = None,
        target_clients: list[str] | None = None,
        connection_config: dict[str, Any] | None = None,
        connection_id: str | None = None,
    ) -> ConversionResult:
        """Convert a design file structure into email HTML via MJML.

        Shim: builds an ``EmailDesignDocument`` via ``from_legacy()`` and
        delegates to ``convert_document_mjml()``.  Falls back to the
        recursive converter if MJML compilation fails (requires full
        DesignNode tree preserved from the original structure).
        """
        from app.design_sync.email_design_document import EmailDesignDocument

        # Normalize once — reused by both from_legacy and recursive fallback
        structure, _norm_stats = normalize_tree(structure, raw_file_data=raw_file_data)

        document = EmailDesignDocument.from_legacy(
            structure,
            tokens,
            selected_nodes=selected_nodes,
            connection_config=connection_config,
            _pre_normalized=True,
        )

        if not document.sections:
            return ConversionResult(html="", sections_count=0, warnings=["No frames found"])

        try:
            return await self.convert_document_mjml(
                document,
                target_clients=target_clients,
                connection_id=connection_id,
            )
        except MjmlCompileError:
            logger.warning("design_sync.mjml_fallback", reason="compilation_failed")
            # Reuse already-normalized structure for recursive fallback
            frames = self._collect_frames(structure, selected_nodes)
            if not frames:
                return ConversionResult(html="", sections_count=0, warnings=["No frames found"])
            layout = document.to_layout_description()
            compat = ConverterCompatibility(target_clients=target_clients)
            return self._convert_recursive(
                frames=frames,
                layout=layout,
                tokens=document.to_extracted_tokens(),
                warnings=["MJML compilation failed, falling back to recursive converter"],
                compat=compat,
                container_width=document.layout.container_width,
                raw_file_data=raw_file_data,
            )

    async def _convert_mjml_from_layout(
        self,
        *,
        layout: DesignLayoutDescription,
        tokens: ExtractedTokens,
        warnings: list[str],
        container_width: int,
        target_clients: list[str] | None = None,
        connection_id: str | None = None,
    ) -> ConversionResult:
        """Generate MJML from layout via template engine, compile via sidecar.

        When *connection_id* is set and caching is enabled, the full compiled result
        is cached keyed by a composite hash of all section hashes. MJML compilation
        requires the full assembled document, so caching is at conversion level.
        """
        # Check async cache (memory + Redis) for full conversion result
        cache_key: str | None = None
        if connection_id and get_settings().design_sync.section_cache_enabled and layout.sections:
            import hashlib

            from app.design_sync.section_cache import compute_section_hash, get_section_cache

            section_hashes = [
                compute_section_hash(
                    s, tokens, container_width=container_width, target_clients=target_clients
                )
                for s in layout.sections
            ]
            cache_key = hashlib.sha256(":".join(section_hashes).encode()).hexdigest()
            cache = get_section_cache()
            cached = await cache.get(connection_id, cache_key)
            if cached is not None:
                section_count = sum(
                    1 for s in layout.sections if s.section_type != EmailSectionType.PREHEADER
                )
                logger.info(
                    "design_sync.mjml_conversion_cache_hit",
                    connection_id=connection_id,
                    sections=section_count,
                )
                return ConversionResult(
                    html=cached.html,
                    sections_count=section_count,
                    warnings=warnings,
                    layout=layout,
                    cache_hit_rate=1.0,
                )

        engine = get_engine()
        ctx = build_template_context(tokens, container_width=container_width)
        preheader = ""
        for s in layout.sections:
            if s.section_type == EmailSectionType.PREHEADER and s.texts:
                preheader = s.texts[0].content
                break
        body_sections = [s for s in layout.sections if s.section_type != EmailSectionType.PREHEADER]
        mjml_str = engine.render_email(
            body_sections,
            ctx,
            preheader=preheader,
        )
        logger.info("design_sync.mjml_template_rendered", sections=len(body_sections))
        compile_result = await self.compile_mjml(mjml_str, target_clients=target_clients)

        if compile_result.errors:
            error_msgs = [e.message for e in compile_result.errors]
            warnings.append(
                f"MJML had {len(compile_result.errors)} validation issues: "
                + "; ".join(error_msgs[:3])
            )

        compiled_html = inject_section_markers(compile_result.html, layout)

        # Count non-preheader sections for sections_count
        section_count = sum(
            1 for s in layout.sections if s.section_type != EmailSectionType.PREHEADER
        )

        # Store in async cache (memory + Redis)
        if connection_id and cache_key:
            from app.design_sync.section_cache import SectionCacheEntry, get_section_cache

            entry = SectionCacheEntry(
                html=compiled_html,
                images=(),
                generated_at=datetime.now(UTC).isoformat(),
            )
            await get_section_cache().set(connection_id, cache_key, entry)

        logger.info(
            "design_sync.mjml_conversion_completed",
            sections=section_count,
            build_time_ms=compile_result.build_time_ms,
            errors=len(compile_result.errors),
        )

        input_button_count = sum(len(s.buttons) for s in layout.sections)
        quality_warnings = run_quality_contracts(
            compiled_html,
            input_section_count=section_count,
            input_button_count=input_button_count,
        )

        return ConversionResult(
            html=compiled_html,
            sections_count=section_count,
            warnings=warnings,
            layout=layout,
            cache_hit_rate=0.0 if connection_id and cache_key else None,
            quality_warnings=quality_warnings,
        )

    def _convert_with_components(
        self,
        *,
        _frames: list[DesignNode],
        layout: DesignLayoutDescription,
        tokens: ExtractedTokens,
        warnings: list[str],
        compat: ConverterCompatibility,
        container_width: int,
        image_urls: dict[str, str] | None = None,
        connection_id: str | None = None,
        section_hashes: dict[str, str] | None = None,
    ) -> ConversionResult:
        """Component-template-based conversion (table-on-table structure)."""
        from app.design_sync.component_matcher import match_all
        from app.design_sync.component_renderer import ComponentRenderer

        # Match sections to components
        matches = match_all(
            layout.sections,
            container_width=container_width,
            image_urls=image_urls,
        )

        # Section cache (sync/memory-only)
        cache = None
        cached_entries: dict[str, Any] = {}
        if connection_id and section_hashes:
            from app.design_sync.section_cache import SectionCacheEntry, get_section_cache

            cache = get_section_cache()
            for node_id, section_hash in section_hashes.items():
                entry = cache.get_sync(connection_id, section_hash)
                if entry is not None:
                    cached_entries[node_id] = entry

        hit_count = 0
        miss_count = 0

        # Render each section using component templates
        renderer = ComponentRenderer(container_width=container_width)
        renderer.load()

        section_parts: list[str] = []
        all_images: list[dict[str, str]] = []

        for match in matches:
            node_id = match.section.node_id
            cached_entry = cached_entries.get(node_id)

            if cached_entry is not None:
                section_parts.append(cached_entry.html)
                all_images.extend(cached_entry.images)
                hit_count += 1
            else:
                rendered = renderer.render_section(match)
                section_parts.append(rendered.html)
                all_images.extend(rendered.images)
                miss_count += 1

                # Store in cache
                if (
                    cache is not None
                    and connection_id is not None
                    and section_hashes
                    and node_id in section_hashes
                ):
                    entry = SectionCacheEntry(
                        html=rendered.html,
                        images=tuple(rendered.images),
                        generated_at=datetime.now(UTC).isoformat(),
                    )
                    cache.set_sync(connection_id, section_hashes[node_id], entry)

            # Inter-section spacer
            if match.spacing_after and match.spacing_after > 0:
                spacer_h = int(match.spacing_after)
                section_parts.append(
                    f"<!--[if mso]>\n"
                    f'<table role="presentation" width="{container_width}" align="center" '
                    f'cellpadding="0" cellspacing="0" border="0"><tr>'
                    f'<td height="{spacer_h}" style="font-size:0;line-height:0;'
                    f'mso-line-height-rule:exactly;">&nbsp;</td></tr></table>\n'
                    f"<![endif]-->\n"
                    f"<!--[if !mso]><!-->\n"
                    f'<div style="height:{spacer_h}px;line-height:{spacer_h}px;'
                    f'font-size:1px;mso-line-height-rule:exactly;">&nbsp;</div>\n'
                    f"<!--<![endif]-->"
                )

        # Adjacent-section bgcolor propagation (Phase 41.2)
        if get_settings().design_sync.bgcolor_propagation_enabled:
            from app.design_sync.bgcolor_propagator import propagate_adjacent_bgcolor

            section_parts = propagate_adjacent_bgcolor(
                matches,
                section_parts,
                connection_id=connection_id,
            )

        sections_html = "\n".join(section_parts)

        # Build style block
        palette = convert_colors_to_palette(tokens.colors)
        typography = convert_typography(tokens.typography)
        bg_color = _sanitize_css_value(palette.background) or "#ffffff"
        safe_body_font = _sanitize_css_value(typography.body_font)
        safe_mso_font = _sanitize_css_value(typography.heading_font) or '"Segoe UI", sans-serif'

        style_block = self._build_component_style_block(
            safe_body_font or "Arial, Helvetica, sans-serif",
            tokens,
        )

        # Dark mode meta tags
        meta_tags = ""
        if tokens.dark_colors:
            meta_tags = dark_mode_meta_tags()

        # Check max-width support
        if compat.has_targets:
            compat.check_and_warn("max-width", context="Email wrapper div")

        result_html = COMPONENT_SHELL.format(
            meta_tags=meta_tags,
            style_block=style_block,
            mso_font=safe_mso_font,
            bg_color=bg_color,
            body_font=safe_body_font or "Arial, Helvetica, sans-serif",
            base_size=typography.base_size or "16px",
            container_width=container_width,
            sections=sections_html,
        )
        result_html = format_email_html(result_html)

        # Cache stats
        total = hit_count + miss_count
        cache_hit_rate: float | None = None
        if total > 0 and connection_id and section_hashes:
            cache_hit_rate = hit_count / total
            logger.info(
                "design_sync.conversion_cache_stats",
                connection_id=connection_id,
                hit_count=hit_count,
                miss_count=miss_count,
                hit_rate=round(cache_hit_rate, 2),
            )

        logger.info(
            "design_sync.component_converter_result",
            sections_count=len(matches),
            warnings_count=len(warnings),
        )

        # Match confidence scores
        match_confidences = {m.section_idx: m.confidence for m in matches}

        input_button_count = sum(len(s.buttons) for s in layout.sections)
        quality_warnings = run_quality_contracts(
            result_html,
            input_section_count=len(matches),
            input_button_count=input_button_count,
        )

        return ConversionResult(
            html=result_html,
            sections_count=len(matches),
            warnings=warnings,
            layout=layout,
            compatibility_hints=compat.hints,
            images=all_images,
            cache_hit_rate=cache_hit_rate,
            quality_warnings=quality_warnings,
            match_confidences=match_confidences,
        )

    def _convert_recursive(
        self,
        *,
        frames: list[DesignNode],
        layout: DesignLayoutDescription,
        tokens: ExtractedTokens,
        warnings: list[str],
        compat: ConverterCompatibility,
        container_width: int,
        raw_file_data: dict[str, Any] | None = None,
    ) -> ConversionResult:
        """Legacy recursive converter (original tr-stacking approach)."""
        # Build O(1) lookup maps from layout analysis
        sections_by_node_id: dict[str, EmailSection] = {
            section.node_id: section for section in layout.sections
        }

        button_node_ids: set[str] = set()
        for section in layout.sections:
            for btn in section.buttons:
                button_node_ids.add(btn.node_id)

        text_meta: dict[str, TextBlock] = {}
        for section in layout.sections:
            for tb in section.texts:
                text_meta[tb.node_id] = tb

        # Build props_map: from raw file data (Penpot) or from DesignNode tree (Figma)
        if raw_file_data:
            props_map = self._build_props_map(raw_file_data)
        else:
            props_map = self._build_props_map_from_nodes(frames)

        # Compute body font size from typography tokens for heading detection
        typography = convert_typography(tokens.typography)
        body_font_size = 16.0
        if typography.base_size:
            with contextlib.suppress(ValueError, TypeError):
                body_font_size = float(typography.base_size.replace("px", ""))

        # Build gradient name → ExtractedGradient lookup
        gradients_map: dict[str, ExtractedGradient] = (
            {g.name: g for g in tokens.gradients} if tokens.gradients else {}
        )

        # Convert each frame to HTML section
        section_parts: list[str] = []
        section_idx = 0
        for frame in frames:
            # Skip childless frames at section level (empty spacer sections)
            if not frame.children:
                continue
            self._collect_vector_warnings(frame, warnings)
            slot_counter: dict[str, int] = {}
            section_html = node_to_email_html(
                frame,
                indent=1,
                props_map=props_map or None,
                section_map=sections_by_node_id,
                button_ids=button_node_ids,
                text_meta=text_meta,
                body_font_size=body_font_size,
                compat=compat,
                gradients_map=gradients_map or None,
                slot_counter=slot_counter,
            )
            section_parts.append(
                f'<tr data-section-id="section_{section_idx}"><td>\n{section_html}\n</td></tr>'
            )
            section_idx += 1

            # Inter-section spacer from layout analysis
            frame_section = sections_by_node_id.get(frame.id)
            if frame_section and frame_section.spacing_after and frame_section.spacing_after > 0:
                spacer_h = int(frame_section.spacing_after)
                section_parts.append(
                    f'<tr><td style="height:{spacer_h}px;font-size:1px;'
                    f'line-height:1px;mso-line-height-rule:exactly;" '
                    f'aria-hidden="true">&nbsp;</td></tr>'
                )

        sections_html = "\n".join(section_parts)

        # Apply token-derived values (sanitize for CSS context)
        palette = convert_colors_to_palette(tokens.colors)
        bg_color = _sanitize_css_value(palette.background) or "#ffffff"
        text_color = _sanitize_css_value(palette.text) or "#000000"

        safe_body_font = _sanitize_css_value(typography.body_font)
        style_block = (
            "<style>\n"
            f"  body {{ font-family: {safe_body_font}; margin: 0; padding: 0; }}\n"
            "  table { border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; }\n"
            "  img { -ms-interpolation-mode: bicubic; border: 0; display: block;"
            " outline: none; text-decoration: none; }\n"
            "</style>"
        )

        # Dark mode CSS (only if dark tokens present)
        if tokens.dark_colors:
            dark_css = dark_mode_style_block(tokens.colors, tokens.dark_colors)
            dark_meta = dark_mode_meta_tags()
            if dark_meta:
                style_block = dark_meta + "\n" + style_block
            if dark_css:
                style_block = style_block + "\n" + dark_css

        # Check max-width support (used on wrapper table)
        if compat.has_targets:
            compat.check_and_warn("max-width", context="Email wrapper table")

        result_html = EMAIL_SKELETON.format(
            style_block=style_block,
            bg_color=bg_color,
            text_color=text_color,
            body_font=safe_body_font or "Arial, Helvetica, sans-serif",
            sections=sections_html,
            container_width=container_width,
        )
        result_html = format_email_html(result_html)

        logger.info(
            "design_sync.converter_result",
            sections_count=len(frames),
            warnings_count=len(warnings),
        )

        input_button_count = sum(len(s.buttons) for s in layout.sections)
        quality_warnings = run_quality_contracts(
            result_html,
            input_section_count=len(frames),
            input_button_count=input_button_count,
        )

        return ConversionResult(
            html=result_html,
            sections_count=len(frames),
            warnings=warnings,
            layout=layout,
            compatibility_hints=compat.hints,
            quality_warnings=quality_warnings,
        )

    @staticmethod
    def _build_component_style_block(body_font: str, tokens: ExtractedTokens) -> str:
        """Build <style> block for component-based shell with responsive utilities."""
        lines = [
            "<style>",
            "  :root {",
            "    color-scheme: light dark;",
            "    supported-color-schemes: light dark;",
            "  }",
            f"  body {{ font-family: {body_font}; margin: 0; padding: 0;"
            " width: 100%; -webkit-text-size-adjust: 100%; }",
            "  img { border: 0; outline: none; text-decoration: none;"
            " -ms-interpolation-mode: bicubic; }",
            "  table { border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; }",
            "  @media only screen and (max-width: 599px) {",
            "    .column { display: block !important; max-width: 100% !important;"
            " width: 100% !important; }",
            "    .bannerimg { width: 100% !important; height: auto !important; }",
            "    .wf { width: 100% !important; }",
            "    .hide { display: none !important; max-height: 0 !important;"
            " overflow: hidden !important; mso-hide: all !important; }",
            "    .db { display: block !important; }",
            "  }",
        ]

        # Component dark mode classes (from email-shell seed)
        lines.extend(
            [
                "  @media (prefers-color-scheme: dark) {",
                "    .dark-bg { background-color: #1a1a2e !important; }",
                "    .dark-text { color: #e0e0e0 !important; }",
                "    .header-bg, .footer-bg, .navbar-bg, .logoheader-bg,",
                "    .preheader-bg, .col2-bg, .col3-bg, .col4-bg,",
                "    .revcol-bg, .social-bg, .textblock-bg,",
                "    .artcard-bg { background-color: #1a1a2e !important; }",
                "    .product-card { background-color: #2d2d44 !important; }",
                "    .header-link, .navbar-link, .preheader-link,",
                "    .footer-link { color: #8ecae6 !important; }",
                "    .footer-text, .social-label, .imgblock-caption { color: #b0b0b0 !important; }",
                "    .product-desc { color: #b0b0b0 !important; }",
                "    .textblock-heading, .artcard-heading, .product-title,",
                "    .hero-title { color: #e0e0e0 !important; }",
                "    .textblock-body, .artcard-body,",
                "    .hero-subtitle { color: #cccccc !important; }",
                "    .product-price { color: #8ecae6 !important; }",
                "    .cta-btn { background-color: #4895ef !important; }",
                "    .cta-btn a { color: #ffffff !important; }",
                "    .cta-ghost { border-color: #8ecae6 !important; }",
                "    .cta-ghost a { color: #8ecae6 !important; }",
                "    .hero-overlay { background-color: rgba(0,0,0,0.7) !important; }",
                "    .divider-line { border-top-color: #444466 !important; }",
                "  }",
                "  [data-ogsc] .dark-bg { background-color: #1a1a2e !important; }",
                "  [data-ogsb] .dark-text { color: #e0e0e0 !important; }",
                "  [data-ogsc] .header-bg, [data-ogsc] .footer-bg, [data-ogsc] .navbar-bg,",
                "  [data-ogsc] .logoheader-bg, [data-ogsc] .preheader-bg,",
                "  [data-ogsc] .col2-bg, [data-ogsc] .col3-bg, [data-ogsc] .col4-bg,",
                "  [data-ogsc] .revcol-bg, [data-ogsc] .social-bg,",
                "  [data-ogsc] .textblock-bg,"
                " [data-ogsc] .artcard-bg { background-color: #1a1a2e !important; }",
                "  [data-ogsc] .product-card { background-color: #2d2d44 !important; }",
                "  [data-ogsc] .header-link, [data-ogsc] .navbar-link,",
                "  [data-ogsc] .preheader-link,"
                " [data-ogsc] .footer-link { color: #8ecae6 !important; }",
                "  [data-ogsc] .footer-text, [data-ogsc] .social-label,",
                "  [data-ogsc] .imgblock-caption { color: #b0b0b0 !important; }",
                "  [data-ogsc] .textblock-heading, [data-ogsc] .artcard-heading,",
                "  [data-ogsc] .product-title,"
                " [data-ogsc] .hero-title { color: #e0e0e0 !important; }",
                "  [data-ogsb] .textblock-body, [data-ogsb] .artcard-body,",
                "  [data-ogsc] .hero-subtitle { color: #cccccc !important; }",
                "  [data-ogsc] .product-price { color: #8ecae6 !important; }",
                "  [data-ogsc] .cta-btn { background-color: #4895ef !important; }",
                "  [data-ogsc] .cta-ghost { border-color: #8ecae6 !important; }",
                "  [data-ogsc] .divider-line { border-top-color: #444466 !important; }",
            ]
        )

        # Token-derived dark mode (additional per-project dark colors)
        if tokens.dark_colors:
            dark_css = dark_mode_style_block(tokens.colors, tokens.dark_colors)
            if dark_css:
                # Strip outer <style></style> tags — we'll close ours
                inner = dark_css.replace("<style>", "").replace("</style>", "").strip()
                if inner:
                    lines.append(f"  {inner}")

        lines.append("</style>")
        return "\n".join(lines)

    def _collect_frames(
        self,
        structure: DesignFileStructure,
        selected_nodes: list[str] | None,
    ) -> list[DesignNode]:
        """Walk pages and collect top-level FRAME/COMPONENT/INSTANCE nodes."""
        frames: list[DesignNode] = []
        frame_types = {DesignNodeType.FRAME, DesignNodeType.COMPONENT, DesignNodeType.INSTANCE}

        for page in structure.pages:
            for child in page.children:
                if child.type in frame_types and (
                    selected_nodes is None or child.id in selected_nodes
                ):
                    # B3: Skip top-level frames with no visible content
                    if not _has_visible_content(child):
                        continue
                    frames.append(child)
        return frames

    def _collect_vector_warnings(self, node: DesignNode, warnings: list[str]) -> None:
        """Recursively collect warnings for VECTOR nodes that will be stripped."""
        if node.type == DesignNodeType.VECTOR:
            warnings.append(
                f"SVG/vector node '{node.name}' (id={node.id}) stripped — not email-safe"
            )
        for child in node.children:
            self._collect_vector_warnings(child, warnings)

    def _build_props_map_from_nodes(self, frames: list[DesignNode]) -> dict[str, _NodeProps]:
        """Build props_map from DesignNode fields (provider-agnostic)."""
        props: dict[str, _NodeProps] = {}

        def _walk(node: DesignNode) -> None:
            has_data = bool(
                node.fill_color
                or node.font_family
                or node.font_size
                or node.font_weight
                or node.padding_top
                or node.padding_right
                or node.padding_bottom
                or node.padding_left
                or node.layout_mode
                or node.item_spacing
                or node.counter_axis_spacing
                or node.line_height_px
                or node.letter_spacing_px
                or node.text_transform
                or node.text_decoration
            )
            if has_data:
                props[node.id] = _NodeProps(
                    bg_color=node.fill_color,
                    font_family=node.font_family,
                    font_size=node.font_size,
                    font_weight=str(node.font_weight) if node.font_weight else None,
                    padding_top=node.padding_top if node.padding_top is not None else 0,
                    padding_right=node.padding_right if node.padding_right is not None else 0,
                    padding_bottom=node.padding_bottom if node.padding_bottom is not None else 0,
                    padding_left=node.padding_left if node.padding_left is not None else 0,
                    layout_direction=(
                        "row"
                        if node.layout_mode == "HORIZONTAL"
                        else "column"
                        if node.layout_mode == "VERTICAL"
                        else None
                    ),
                    item_spacing=node.item_spacing if node.item_spacing is not None else 0,
                    counter_axis_spacing=node.counter_axis_spacing
                    if node.counter_axis_spacing is not None
                    else 0,
                    line_height_px=node.line_height_px,
                    letter_spacing_px=node.letter_spacing_px,
                    text_transform=node.text_transform,
                    text_decoration=node.text_decoration,
                )
            for child in node.children:
                _walk(child)

        for frame in frames:
            _walk(frame)
        return props

    def _build_props_map(self, file_data: dict[str, Any]) -> dict[str, _NodeProps]:
        """Extract visual properties from raw Penpot objects."""
        props: dict[str, _NodeProps] = {}
        pages_index = file_data.get("data", {}).get("pages-index", {})
        for page_data in pages_index.values():
            if not isinstance(page_data, dict):
                continue
            for obj_id, obj in page_data.get("objects", {}).items():
                if not isinstance(obj, dict):
                    continue
                bg = self._extract_bg(obj)
                font = obj.get("font-family")
                size = obj.get("font-size")
                weight = str(obj.get("font-weight", "")) or None
                padding = obj.get("layout-padding", {})
                if not isinstance(padding, dict):
                    padding = {}
                props[str(obj_id)] = _NodeProps(
                    bg_color=bg,
                    font_family=str(font) if font else None,
                    font_size=float(size) if size else None,
                    font_weight=weight,
                    padding_top=float(padding.get("p1", 0)),
                    padding_right=float(padding.get("p2", 0)),
                    padding_bottom=float(padding.get("p3", 0)),
                    padding_left=float(padding.get("p4", 0)),
                    layout_direction=str(obj.get("layout-flex-dir"))
                    if obj.get("layout-flex-dir")
                    else None,
                    item_spacing=float(obj.get("layout-gap", {}).get("row-gap", 0))
                    if isinstance(obj.get("layout-gap"), dict)
                    else 0,
                    counter_axis_spacing=float(obj.get("layout-gap", {}).get("column-gap", 0))
                    if isinstance(obj.get("layout-gap"), dict)
                    else 0,
                )
        return props

    async def compile_mjml(
        self,
        mjml: str,
        *,
        target_clients: list[str] | None = None,
    ) -> MjmlCompileResult:
        """Compile MJML markup to email HTML via the Maizzle sidecar."""
        url = get_settings().maizzle_builder_url
        payload: dict[str, object] = {"mjml": mjml}
        if target_clients:
            payload["target_clients"] = target_clients

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{url}/compile-mjml", json=payload)
                response.raise_for_status()
                data = response.json()

                errors = [
                    MjmlError(
                        line=e.get("line", 0),
                        message=e.get("message", ""),
                        tag_name=e.get("tagName", ""),
                    )
                    for e in data.get("errors", [])
                ]
                return MjmlCompileResult(
                    html=str(data["html"]),
                    errors=errors,
                    build_time_ms=float(data.get("build_time_ms", 0)),
                    optimization=data.get("optimization"),
                )
        except httpx.ConnectError as exc:
            logger.error("design_sync.mjml_compile_unavailable", error=str(exc))
            raise MjmlCompileError("Cannot connect to maizzle-builder service") from exc
        except httpx.HTTPStatusError as exc:
            logger.error(
                "design_sync.mjml_compile_error",
                status_code=exc.response.status_code,
            )
            raise MjmlCompileError("MJML compilation failed") from exc
        except ValueError as exc:
            logger.error("design_sync.mjml_compile_invalid_response", error=str(exc))
            raise MjmlCompileError("Invalid response from maizzle-builder service") from exc

    @staticmethod
    def _extract_bg(obj: dict[str, Any]) -> str | None:
        """Extract first solid fill color from Penpot fills array."""
        fills = obj.get("fills", [])
        if not isinstance(fills, list):
            return None
        for fill in fills:
            if isinstance(fill, dict) and fill.get("fill-color"):
                return str(fill["fill-color"])
        return None


# Backward-compatible alias
PenpotConverterService = DesignConverterService


def build_component_style_block(body_font: str, tokens: ExtractedTokens) -> str:
    """Build <style> block for component-based shell.

    Public module-level wrapper around the static method for external callers
    (e.g. diagnostic runner).
    """
    return DesignConverterService._build_component_style_block(body_font, tokens)


async def enhance_layout_with_ai(
    layout: DesignLayoutDescription,
) -> DesignLayoutDescription:
    """Post-process layout analysis with AI classification and content role detection.

    Called after sync analyze_layout() by async service layers.
    Skipped entirely when DESIGN_SYNC__AI_LAYOUT_ENABLED is False.

    Returns a new DesignLayoutDescription with enhanced sections.
    """
    settings = get_settings()
    if not settings.design_sync.ai_layout_enabled:
        return layout

    if not layout.sections:
        return layout

    sections = list(layout.sections)

    # 1. AI classification for UNKNOWN sections
    unknown_sections = [s for s in sections if s.section_type == EmailSectionType.UNKNOWN]
    if unknown_sections:
        from app.design_sync.ai_layout_classifier import classify_sections_batch

        all_types = [s.section_type.value for s in sections]
        all_ids = [s.node_id for s in sections]
        classifications = await classify_sections_batch(
            unknown_sections,
            all_section_types=all_types,
            all_node_ids=all_ids,
        )

        # Build lookup: node_id -> classification
        classification_map = {
            s.node_id: c for s, c in zip(unknown_sections, classifications, strict=True)
        }

        # Replace sections with AI-classified versions
        new_sections: list[EmailSection] = []
        for s in sections:
            if s.node_id in classification_map:
                c = classification_map[s.node_id]
                try:
                    new_type = EmailSectionType(c.section_type)
                except ValueError:
                    new_type = EmailSectionType.UNKNOWN
                new_sections.append(
                    replace(
                        s,
                        section_type=new_type,
                        classification_confidence=c.confidence,
                    )
                )
            else:
                new_sections.append(s)
        sections = new_sections

    # 2. Content role detection
    from app.design_sync.ai_content_detector import detect_content_roles

    annotations = await detect_content_roles(sections)

    # Merge annotations into sections
    role_map = {a.section_node_id: a.roles for a in annotations}
    enhanced: list[EmailSection] = []
    for s in sections:
        roles = role_map.get(s.node_id, ())
        if roles:
            enhanced.append(replace(s, content_roles=roles))
        else:
            enhanced.append(s)

    return replace(layout, sections=enhanced)
