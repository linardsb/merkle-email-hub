"""Deterministic HTML assembly from structured plan + golden template.

This module contains ZERO LLM calls. It takes an EmailBuildPlan and
a GoldenTemplate and produces final HTML through string operations.
"""

import re
from typing import Final

from app.ai.agents.schemas.build_plan import (
    DesignTokens,
    EmailBuildPlan,
    SectionDecision,
)
from app.ai.templates import GoldenTemplate, TemplateRegistry, get_template_registry
from app.core.logging import get_logger

logger = get_logger(__name__)

# CSS custom property → EmailBuildPlan.design_tokens field mapping
_TOKEN_CSS_MAP: Final[dict[str, str]] = {
    "--color-primary": "primary_color",
    "--color-secondary": "secondary_color",
    "--color-bg": "background_color",
    "--color-text": "text_color",
    "--font-body": "font_family",
    "--font-heading": "heading_font_family",
    "--border-radius": "border_radius",
}


class AssemblyError(Exception):
    """Raised when deterministic assembly fails (e.g. missing template)."""


class TemplateAssembler:
    """Deterministic HTML assembly from structured plan + golden template."""

    def __init__(self, registry: TemplateRegistry | None = None) -> None:
        self._registry = registry or get_template_registry()

    def assemble(self, plan: EmailBuildPlan) -> str:
        """Assemble final HTML from plan. 100% deterministic.

        Steps:
        1. Resolve golden template by plan.template.template_name (with fallback)
        2. Fill slots with plan.slot_fills via registry.fill_slots()
        3. Apply design tokens (CSS custom property injection)
        4. Apply section decisions (show/hide, background overrides)
        5. Set preheader text
        """
        template = self._resolve_template(plan)

        # Step 1: Fill slots
        fills = {sf.slot_id: sf.content for sf in plan.slot_fills}
        html = self._registry.fill_slots(template, fills)

        # Step 2: Apply design tokens
        html = self._apply_design_tokens(html, plan.design_tokens)

        # Step 3: Apply section decisions
        for section in plan.sections:
            html = self._apply_section(html, section)

        # Step 4: Set preheader
        if plan.preheader_text:
            html = self._set_preheader(html, plan.preheader_text)

        logger.info(
            "scaffolder.assembly_completed",
            template=plan.template.template_name,
            slots_filled=len(fills),
            html_length=len(html),
        )
        return html

    def _resolve_template(self, plan: EmailBuildPlan) -> GoldenTemplate:
        """Resolve template by name, falling back to fallback_template."""
        template = self._registry.get(plan.template.template_name)
        if template is None and plan.template.fallback_template:
            template = self._registry.get(plan.template.fallback_template)
        if template is None:
            raise AssemblyError(
                f"Template '{plan.template.template_name}' not found. "
                f"Available: {self._registry.names()}"
            )
        return template

    def _apply_design_tokens(self, html: str, tokens: DesignTokens) -> str:
        """Replace CSS custom property fallback values with design token values.

        Targets patterns like: var(--color-primary, #default)
        Replaces with the token value directly (inline-safe).
        Uses lambda replacement to avoid backreference issues in re.sub.
        """
        for css_prop, attr_name in _TOKEN_CSS_MAP.items():
            value: str = getattr(tokens, attr_name)
            pattern = re.compile(rf"var\({re.escape(css_prop)},\s*[^)]+\)")
            html = pattern.sub(lambda _m, v=value: v, html)  # type: ignore[misc]
        return html

    def _apply_section(self, html: str, section: SectionDecision) -> str:
        """Apply a single section decision (hide or change background)."""
        if section.hidden:
            # Remove entire section element by data-section attribute
            pattern = re.compile(
                r"<(\w+)\b[^>]*\bdata-section=[\"']"
                + re.escape(section.section_name)
                + r"[\"'][^>]*>.*?</\1>",
                re.DOTALL,
            )
            html = pattern.sub("", html, count=1)
        elif section.background_color:
            # Prepend background-color to existing style attribute
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

    def _set_preheader(self, html: str, preheader: str) -> str:
        """Set preheader text via data-slot='preheader' element."""
        if 'data-slot="preheader"' not in html and "data-slot='preheader'" not in html:
            return html
        pattern = re.compile(
            r"(<(\w+)\b[^>]*\bdata-slot=[\"']preheader[\"'][^>]*>)(.*?)(</\2>)",
            re.DOTALL,
        )
        return pattern.sub(lambda m: m.group(1) + preheader + m.group(4), html, count=1)
