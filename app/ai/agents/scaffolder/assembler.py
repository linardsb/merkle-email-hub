"""Deterministic HTML assembly from structured plan + golden template.

This module contains ZERO LLM calls. It takes an EmailBuildPlan and
a GoldenTemplate and produces final HTML through role-based replacement.
"""

from __future__ import annotations

import re
from dataclasses import replace as dc_replace
from html import escape as html_escape
from typing import TYPE_CHECKING

from app.ai.agents.schemas.build_plan import (
    DesignTokens,
    EmailBuildPlan,
    SectionDecision,
)
from app.ai.templates import GoldenTemplate, TemplateRegistry, get_template_registry
from app.ai.templates.models import DefaultTokens
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.projects.design_system import DesignSystem, LogoConfig, SocialLink

logger = get_logger(__name__)


class AssemblyError(Exception):
    """Raised when deterministic assembly fails (e.g. missing template)."""


class TemplateAssembler:
    """Deterministic HTML assembly from structured plan + golden template."""

    def __init__(
        self,
        registry: TemplateRegistry | None = None,
        design_system: DesignSystem | None = None,
    ) -> None:
        self._registry = registry or get_template_registry()
        self._design_system = design_system
        self._used_preoptimized = False

    def assemble(self, plan: EmailBuildPlan) -> str:
        """Assemble final HTML. 100% deterministic. Design-system-agnostic."""
        template = self._resolve_template(plan)

        # Use pre-optimized HTML if available (26.3)
        if template.optimized_html is not None:
            template = dc_replace(template, html=template.optimized_html)
            self._used_preoptimized = True
        else:
            self._used_preoptimized = False

        # Step 1: Fill slots
        fills = {sf.slot_id: sf.content for sf in plan.slot_fills}
        html = self._registry.fill_slots(template, fills)

        # Step 2: Role-based palette replacement (template defaults)
        if template.default_tokens is not None and plan.design_tokens.colors:
            html = self._apply_palette_replacement(
                html,
                template.default_tokens,
                plan.design_tokens,
            )

        # Step 2b: Role-based palette replacement (composed component defaults)
        if plan.design_tokens.colors:
            html = self._apply_component_palette_replacement(
                html,
                template,
                plan.design_tokens,
            )

        # Step 3: Font replacement
        if template.default_tokens is not None and plan.design_tokens.fonts:
            html = self._apply_font_replacement(
                html,
                template.default_tokens,
                plan.design_tokens,
            )

        # Step 4: Logo dimension enforcement
        if self._design_system is not None and self._design_system.logo:
            html = self._enforce_logo_dimensions(html, self._design_system.logo)

        # Step 5: Social link injection
        if self._design_system is not None and self._design_system.social_links:
            html = self._inject_social_links(html, self._design_system.social_links)

        # Step 6: Dark mode replacement
        if template.default_tokens is not None and plan.design_tokens.colors:
            html = self._apply_dark_mode_replacement(
                html,
                template.default_tokens,
                plan.design_tokens,
            )

        # Step 7: Brand color sweep (safety net)
        if plan.design_tokens.source == "design_system" and plan.design_tokens.colors:
            html = self._brand_color_sweep(html, plan.design_tokens.colors)

        # Step 8: Apply section decisions
        for section in plan.sections:
            html = self._apply_section(html, section)

        # Step 9: Set preheader
        if plan.preheader_text:
            html = self._set_preheader(html, plan.preheader_text)

        # Step 10: Add builder annotations for roundtrip fidelity (last — after all content is set)
        html = self._add_builder_annotations(html, plan)

        # Step 11: Apply tier strategy (progressive enhancement for MSO)
        html = self._apply_tier_strategy(html, plan)

        logger.info(
            "scaffolder.assembly_completed",
            template=plan.template.template_name,
            slots_filled=len(fills),
            html_length=len(html),
            design_source=plan.design_tokens.source,
            color_roles=len(plan.design_tokens.colors),
        )
        return html

    @property
    def used_preoptimized(self) -> bool:
        """Whether the last assemble() used pre-optimized template HTML."""
        return self._used_preoptimized

    def _resolve_template(self, plan: EmailBuildPlan) -> GoldenTemplate:
        """Resolve template by name. Delegates to TemplateComposer for '__compose__'."""
        if plan.template.template_name == "__compose__":
            return self._compose_template(plan)

        template = self._registry.get(plan.template.template_name)
        if template is None and plan.template.fallback_template:
            template = self._registry.get(plan.template.fallback_template)
        if template is None:
            raise AssemblyError(
                f"Template '{plan.template.template_name}' not found. "
                f"Available: {self._registry.names()}"
            )
        return template

    def _compose_template(self, plan: EmailBuildPlan) -> GoldenTemplate:
        """Compose template from section blocks. Falls back on failure."""
        from app.ai.templates.composer import CompositionError, get_composer

        composer = get_composer()
        section_order = list(plan.template.section_order)

        if not section_order:
            raise AssemblyError("Composition mode ('__compose__') requires non-empty section_order")

        try:
            composed = composer.compose(section_order)
            logger.info(
                "scaffolder.composition_completed",
                sections=section_order,
                slots=len(composed.slots),
            )
            return composed
        except CompositionError as e:
            if plan.template.fallback_template:
                fallback = self._registry.get(plan.template.fallback_template)
                if fallback:
                    logger.warning(
                        "scaffolder.composition_fallback",
                        error=str(e),
                        fallback=plan.template.fallback_template,
                    )
                    return fallback

            raise AssemblyError(f"Composition failed: {e}. No fallback template available.") from e

    # ── Palette replacement ──

    def _apply_palette_replacement(
        self,
        html: str,
        defaults: DefaultTokens,
        tokens: DesignTokens,
    ) -> str:
        """Replace template default colors with client colors, matched by role.

        For each role in the template's default_tokens.colors:
        1. Look up the default hex (what's in the template HTML)
        2. Look up the client's hex for the same role
        3. Global find-replace (case-insensitive)
        """
        for role, default_hex in defaults.colors.items():
            if role.startswith("dark_"):
                continue
            client_hex = tokens.colors.get(role)
            if client_hex is None or client_hex.lower() == default_hex.lower():
                continue
            html = re.sub(re.escape(default_hex), client_hex, html, flags=re.IGNORECASE)
        return html

    def _apply_component_palette_replacement(
        self,
        html: str,
        template: GoldenTemplate,
        tokens: DesignTokens,
    ) -> str:
        """Apply palette replacement for each composed SectionBlock's default_tokens."""
        from app.ai.templates.composer import SectionBlock

        composed: tuple[SectionBlock, ...] | None = getattr(template, "composed_sections", None)
        if not composed:
            return html

        for section in composed:
            if section.default_tokens is not None:
                html = self._apply_palette_replacement(
                    html,
                    section.default_tokens,
                    tokens,
                )
        return html

    # ── Font replacement ──

    def _apply_font_replacement(
        self,
        html: str,
        defaults: DefaultTokens,
        tokens: DesignTokens,
    ) -> str:
        """Replace template default font stacks with client fonts, matched by role."""
        for role, default_stack in defaults.fonts.items():
            client_stack = tokens.fonts.get(role)
            if client_stack is None or client_stack == default_stack:
                continue
            html = html.replace(default_stack, client_stack)

        # Replace base font size if different
        default_base = defaults.font_sizes.get("base", "16px")
        client_base = tokens.font_sizes.get("base")
        if client_base and client_base != default_base:
            html = html.replace(
                f"font-size: {default_base}",
                f"font-size: {client_base}",
                1,
            )

        # Replace border-radius
        default_radius = defaults.spacing.get("border_radius", "4px")
        client_radius = tokens.spacing.get("border_radius")
        if client_radius and client_radius != default_radius:
            html = html.replace(
                f"border-radius: {default_radius}",
                f"border-radius: {client_radius}",
            )

        return html

    # ── Dark mode ──

    def _apply_dark_mode_replacement(
        self,
        html: str,
        defaults: DefaultTokens,
        tokens: DesignTokens,
    ) -> str:
        """Replace dark mode colors in CSS blocks."""
        for role, default_hex in defaults.colors.items():
            if not role.startswith("dark_"):
                continue
            client_hex = tokens.colors.get(role)
            if client_hex is None or client_hex.lower() == default_hex.lower():
                continue
            html = re.sub(re.escape(default_hex), client_hex, html, flags=re.IGNORECASE)
        return html

    # ── Logo enforcement ──

    def _enforce_logo_dimensions(self, html: str, logo: LogoConfig) -> str:
        """Set width/height attributes on logo img tags."""
        logo_pattern = re.compile(
            r'(<img\b[^>]*data-slot=["\'](?:logo_url|hero_logo|logo)["\'][^>]*?)(/?>)',
            re.IGNORECASE,
        )

        def _enforce(m: re.Match[str]) -> str:
            tag = m.group(1)
            close = m.group(2)
            tag = re.sub(r'\bwidth=["\']\d+["\']', f'width="{logo.width}"', tag)
            if "width=" not in tag:
                tag += f' width="{logo.width}"'
            tag = re.sub(r'\bheight=["\']\d+["\']', f'height="{logo.height}"', tag)
            if "height=" not in tag:
                tag += f' height="{logo.height}"'
            return tag + close

        return logo_pattern.sub(_enforce, html)

    # ── Social links ──

    def _inject_social_links(self, html: str, social_links: tuple[SocialLink, ...]) -> str:
        """Inject social links into social_links slot if present."""
        if not social_links:
            return html

        parts: list[str] = []
        for link in social_links:
            safe_url = html_escape(link.url, quote=True)
            if link.icon_url:
                safe_icon = html_escape(link.icon_url, quote=True)
                parts.append(
                    f'<a href="{safe_url}" style="display:inline-block;margin:0 8px;">'
                    f'<img src="{safe_icon}" alt="{link.platform}" width="24" height="24" '
                    f'style="display:block;border:0;"></a>'
                )
            else:
                parts.append(
                    f'<a href="{safe_url}" style="display:inline-block;margin:0 8px;'
                    f'font-size:12px;text-decoration:none;">{link.platform.title()}</a>'
                )

        social_html = '<div style="text-align:center;padding:16px 0;">' + "".join(parts) + "</div>"

        if 'data-slot="social_links"' in html or "data-slot='social_links'" in html:
            pattern = re.compile(
                r"(<(\w+)\b[^>]*\bdata-slot=[\"']social_links[\"'][^>]*>)(.*?)(</\2>)",
                re.DOTALL,
            )
            return pattern.sub(lambda m: m.group(1) + social_html + m.group(4), html, count=1)

        return html

    # ── Brand color sweep ──

    def _brand_color_sweep(self, html: str, client_colors: dict[str, str]) -> str:
        """Final safety net: replace off-palette colors with nearest palette match.

        Scans inline CSS color properties. Any hex NOT in the client's palette
        -> replaced with nearest match (Euclidean RGB distance).
        """
        allowlist: set[str] = {c.lower() for c in client_colors.values()}
        allowlist.update({"#ffffff", "#000000"})

        palette_rgb = {c: _hex_to_rgb(c) for c in allowlist}

        def _replace(m: re.Match[str]) -> str:
            prefix, color = m.group(1), m.group(2).lower()
            if color in allowlist:
                return prefix + color
            return prefix + _nearest_color(color, palette_rgb)

        return _HEX_IN_STYLE_RE.sub(_replace, html)

    # ── Section decisions ──

    def _apply_section(self, html: str, section: SectionDecision) -> str:
        """Apply a single section decision (hide or change background)."""
        if section.hidden:
            pattern = re.compile(
                r"<(\w+)\b[^>]*\bdata-section=[\"']"
                + re.escape(section.section_name)
                + r"[\"'][^>]*>.*?</\1>",
                re.DOTALL,
            )
            html = pattern.sub("", html, count=1)
        elif section.background_color:
            pattern = re.compile(
                r"(<[^>]+\bdata-section=[\"']"
                + re.escape(section.section_name)
                + r"[\"'][^>]*\bstyle=[\"'])([^\"']*)"
            )
            html = pattern.sub(
                lambda m: m.group(1) + f"background-color:{section.background_color};" + m.group(2),
                html,
                count=1,
            )
        return html

    def _add_builder_annotations(self, html: str, plan: EmailBuildPlan) -> str:
        """Add data-section-id and data-slot-name attributes for builder sync."""
        # Add data-section-id to elements that have data-section attributes
        for section in plan.sections:
            section_name = section.section_name
            if f'data-section-id="{section_name}"' in html:
                continue  # Already annotated — skip to avoid duplicates
            pattern = re.compile(
                r"(<[^>]+\bdata-section=[\"'])" + re.escape(section_name) + r"([\"'])",
            )
            replacement = rf'\g<0> data-section-id="{section_name}"'
            html = pattern.sub(replacement, html, count=1)

        # Add data-slot-name to elements that have data-slot attributes
        slot_pattern = re.compile(
            r'(<[^>]+\bdata-slot=["\'])([^"\']+)(["\'])',
        )

        def _add_slot_name(m: re.Match[str]) -> str:
            slot_name = m.group(2)
            full_match = m.group(0)
            if "data-slot-name=" not in full_match:
                return full_match + f' data-slot-name="{slot_name}"'
            return full_match

        html = slot_pattern.sub(_add_slot_name, html)

        return html

    def _set_preheader(self, html: str, preheader: str) -> str:
        """Set preheader text via data-slot='preheader' element."""
        if 'data-slot="preheader"' not in html and "data-slot='preheader'" not in html:
            return html
        pattern = re.compile(
            r"(<(\w+)\b[^>]*\bdata-slot=[\"']preheader[\"'][^>]*>)(.*?)(</\2>)",
            re.DOTALL,
        )
        return pattern.sub(lambda m: m.group(1) + preheader + m.group(4), html, count=1)

    # ── Tier strategy (24B.3 Progressive Enhancement Assembly) ──

    def _apply_tier_strategy(self, html: str, plan: EmailBuildPlan) -> str:
        """Apply progressive enhancement tier strategy.

        'universal' = no-op (current behavior preserved).
        'progressive' = detect modern CSS sections, wrap in MSO conditionals
        with table-based fallback for Word engine.
        """
        if plan.tier_strategy != "progressive":
            return html

        # Detect sections with modern CSS (flexbox, grid, border-radius on structural elements)
        modern_css_re = re.compile(
            r'style="[^"]*(?:display\s*:\s*(?:flex|grid|inline-flex|inline-grid)|'
            r'border-radius\s*:\s*(?!0))[^"]*"',
            re.IGNORECASE,
        )

        # Find sections that use modern CSS
        section_re = re.compile(
            r'(<(?:tr|td|div)\b[^>]*\bdata-section=["\'][^"\']+["\'][^>]*>)(.*?)(</(?:tr|td|div)>)',
            re.DOTALL | re.IGNORECASE,
        )

        def _wrap_section(m: re.Match[str]) -> str:
            open_tag = m.group(1)
            content = m.group(2)
            close_tag = m.group(3)
            full_section = open_tag + content + close_tag

            if not modern_css_re.search(full_section):
                return full_section

            fallback = self._generate_word_fallback(full_section)
            return self._wrap_mso_conditional(full_section, fallback)

        return section_re.sub(_wrap_section, html)

    @staticmethod
    def _generate_word_fallback(section_html: str) -> str:
        """Generate a Word-engine-compatible fallback for a section.

        Strips flexbox/grid -> display:block, strips border-radius on td/table,
        wraps background images in VML v:rect pattern.
        """
        fallback = section_html

        # Strip flexbox/grid -> replace with display: block
        fallback = re.sub(
            r"display\s*:\s*(?:flex|grid|inline-flex|inline-grid)",
            "display: block",
            fallback,
            flags=re.IGNORECASE,
        )

        # Strip border-radius on structural elements (td, table, th)
        fallback = re.sub(
            r"(border-radius\s*:\s*)[^;]+;?",
            "",
            fallback,
            flags=re.IGNORECASE,
        )

        # Wrap background images in VML v:rect
        bg_image_re = re.compile(
            r'(<(?:td|table|div)\b[^>]*?)style="([^"]*background-image\s*:\s*url\([\'"]?([^)\'"]+)[\'"]?\)[^"]*)"',
            re.IGNORECASE,
        )

        def _vml_wrap(m: re.Match[str]) -> str:
            tag_start = m.group(1)
            style = m.group(2)
            image_url = m.group(3)
            # Remove background-image from inline style
            clean_style = re.sub(r"background-image\s*:\s*url\([^)]+\)\s*;?\s*", "", style)
            return f'{tag_start}style="{clean_style}" background="{image_url}"'

        fallback = bg_image_re.sub(_vml_wrap, fallback)

        return fallback

    @staticmethod
    def _wrap_mso_conditional(enhanced: str, fallback: str) -> str:
        """Wrap enhanced HTML with MSO conditional comments.

        Non-MSO clients get the enhanced version.
        MSO (Outlook Word engine) gets the fallback.
        """
        return (
            "<!--[if !mso]><!-->\n"
            f"{enhanced}\n"
            "<!--<![endif]-->\n"
            "<!--[if mso]>\n"
            f"{fallback}\n"
            "<![endif]-->"
        )


# ── Module-level helpers ──

_HEX_IN_STYLE_RE = re.compile(
    r"((?:color|background-color|background|border-color)\s*:\s*)(#[0-9a-fA-F]{6})",
)


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _nearest_color(target: str, palette: dict[str, tuple[int, int, int]]) -> str:
    t = _hex_to_rgb(target)
    best, best_d = target, float("inf")
    for hex_c, rgb in palette.items():
        d = sum((a - b) ** 2 for a, b in zip(t, rgb, strict=True))
        if d < best_d:
            best, best_d = hex_c, d
    return best
