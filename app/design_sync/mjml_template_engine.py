"""Jinja2-based MJML section template renderer.

Renders pre-built MJML templates for common email section types, injecting
design tokens (palette, typography, spacing) from the Figma/Penpot design file.
Pure functions — no I/O, no async.
"""

from __future__ import annotations

import functools
import html as html_mod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.design_sync.converter import (
    _sanitize_css_value,
    convert_colors_to_palette,
    convert_typography,
)
from app.design_sync.figma.layout_analyzer import (
    ColumnLayout,
    EmailSection,
    EmailSectionType,
)

if TYPE_CHECKING:
    from app.design_sync.protocol import ExtractedColor, ExtractedTokens
    from app.projects.design_system import BrandPalette, Typography

_TEMPLATE_DIR = Path(__file__).parent / "mjml_templates"

# Section type → template filename
_SECTION_TEMPLATE_MAP: dict[EmailSectionType, str] = {
    EmailSectionType.HERO: "hero.mjml.j2",
    EmailSectionType.HEADER: "header.mjml.j2",
    EmailSectionType.CTA: "cta.mjml.j2",
    EmailSectionType.FOOTER: "footer.mjml.j2",
    EmailSectionType.SOCIAL: "footer.mjml.j2",
    EmailSectionType.SPACER: "spacer.mjml.j2",
    EmailSectionType.DIVIDER: "spacer.mjml.j2",
    EmailSectionType.NAV: "header.mjml.j2",
}

# Column layout → content template (for CONTENT / UNKNOWN with content)
_COLUMN_TEMPLATE_MAP: dict[ColumnLayout, str] = {
    ColumnLayout.SINGLE: "content_single.mjml.j2",
    ColumnLayout.TWO_COLUMN: "content_two_col.mjml.j2",
    ColumnLayout.THREE_COLUMN: "content_three_col.mjml.j2",
    ColumnLayout.MULTI_COLUMN: "content_multi_col.mjml.j2",
}


@dataclass(frozen=True)
class MjmlTemplateContext:
    """Context passed to every MJML Jinja2 template."""

    palette: BrandPalette
    typography: Typography
    dark_colors: tuple[ExtractedColor, ...] = ()
    container_width: int = 600
    section_padding: str = "20px 0"


class MjmlTemplateEngine:
    """Jinja2-based MJML section template renderer.

    Templates live in ``app/design_sync/mjml_templates/`` and are read-only.
    All injected values are HTML-escaped via Jinja2 ``autoescape``.
    """

    def __init__(self, template_dir: Path | None = None) -> None:
        resolved = template_dir or _TEMPLATE_DIR
        self._env = Environment(
            loader=FileSystemLoader(str(resolved)),
            autoescape=select_autoescape(default_for_string=True, default=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._template_dir = resolved

    def resolve_template_name(self, section: EmailSection) -> str:
        """Map an EmailSection to its MJML template filename."""
        # CONTENT / UNKNOWN: image-only → full-width image template
        if section.section_type in (
            EmailSectionType.CONTENT,
            EmailSectionType.UNKNOWN,
        ):
            if section.images and not section.texts and not section.buttons:
                return "image_full.mjml.j2"
            return _COLUMN_TEMPLATE_MAP.get(section.column_layout, "content_single.mjml.j2")

        return _SECTION_TEMPLATE_MAP.get(section.section_type, "content_single.mjml.j2")

    def render_section(
        self,
        section: EmailSection,
        ctx: MjmlTemplateContext,
    ) -> str:
        """Render one EmailSection to MJML markup (no ``<mjml>``/``<mj-body>`` wrapper)."""
        template_name = self.resolve_template_name(section)
        template = self._env.get_template(template_name)
        rendered: str = template.render(
            section=section,
            palette=ctx.palette,
            typo=ctx.typography,
            dark_colors=ctx.dark_colors,
            container_width=ctx.container_width,
            section_padding=ctx.section_padding,
        )
        return rendered

    def render_email(
        self,
        sections: list[EmailSection],
        ctx: MjmlTemplateContext,
        *,
        preheader: str = "",
    ) -> str:
        """Render a complete MJML document from sections."""
        parts: list[str] = []
        for section in sections:
            parts.append(self.render_section(section, ctx))

        dark_css = _build_dark_mode_css(ctx.dark_colors)
        body_mjml = "\n".join(parts)
        body_font = ctx.typography.body_font or "Arial, Helvetica, sans-serif"
        base_size = ctx.typography.base_size or "16px"
        body_lh = ctx.typography.body_line_height or "24px"
        text_color = ctx.palette.text or "#000000"
        bg_color = ctx.palette.background or "#ffffff"

        return _MJML_DOC.format(
            container_width=ctx.container_width,
            body_font=_sanitize_css_value(body_font) or body_font,
            base_size=base_size,
            body_lh=body_lh,
            text_color=text_color,
            bg_color=bg_color,
            preheader=html_mod.escape(preheader),
            dark_css=dark_css,
            body=body_mjml,
        )


@functools.lru_cache(maxsize=1)
def get_engine() -> MjmlTemplateEngine:
    """Return a module-level singleton engine (templates are read-only)."""
    return MjmlTemplateEngine()


def build_template_context(
    tokens: ExtractedTokens,
    *,
    container_width: int = 600,
) -> MjmlTemplateContext:
    """Build an MjmlTemplateContext from raw ExtractedTokens."""
    palette = convert_colors_to_palette(tokens.colors)
    typography = convert_typography(tokens.typography)
    dark = tuple(tokens.dark_colors) if tokens.dark_colors else ()

    return MjmlTemplateContext(
        palette=palette,
        typography=typography,
        dark_colors=dark,
        container_width=container_width,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_dark_mode_css(dark_colors: tuple[ExtractedColor, ...]) -> str:
    """Generate ``@media (prefers-color-scheme: dark)`` CSS block."""
    if not dark_colors:
        return ""
    rules: list[str] = []
    for dc in dark_colors:
        name = _sanitize_css_value(dc.name.lower().replace(" ", "-"))
        hex_val = _sanitize_css_value(dc.hex)
        if not name or not hex_val:
            continue
        rules.append(f"    .dark-{name} {{ color: {hex_val} !important; }}")
    return "@media (prefers-color-scheme: dark) {\n" + "\n".join(rules) + "\n  }"


_MJML_DOC = """\
<mjml>
  <mj-head>
    <mj-attributes>
      <mj-all font-family="{body_font}" />
      <mj-text font-size="{base_size}" line-height="{body_lh}" color="{text_color}" />
      <mj-body width="{container_width}px" />
    </mj-attributes>
    <mj-preview>{preheader}</mj-preview>
    <mj-style>
      {dark_css}
    </mj-style>
  </mj-head>
  <mj-body width="{container_width}px" background-color="{bg_color}">
{body}
  </mj-body>
</mjml>"""
