"""Compose email templates from reusable section blocks.

Used when no golden template matches the brief well.
Section blocks are pre-validated HTML fragments derived from golden templates.
Composition is deterministic — ZERO LLM involvement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.ai.templates.models import (
    DefaultTokens,
    GoldenTemplate,
    SlotType,
    TemplateMetadata,
    TemplateSlot,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

SECTIONS_DIR = Path(__file__).parent / "sections"


@dataclass(frozen=True)
class SectionBlock:
    """A reusable email section block derived from golden templates."""

    block_id: str
    display_name: str
    html: str
    slot_definitions: tuple[TemplateSlot, ...]
    has_mso_wrapper: bool = False
    dark_mode_classes: tuple[str, ...] = ()
    default_tokens: DefaultTokens | None = None


class TemplateComposer:
    """Compose a template from ordered section blocks when no golden template matches.

    Section blocks are loaded from `sections/` directory.
    Composition: skeleton (DOCTYPE/head/body wrapper) + ordered section blocks.
    """

    def __init__(self) -> None:
        self._sections: dict[str, SectionBlock] = {}
        self._skeleton: str = ""
        self._loaded = False

    def load(self) -> None:
        """Load skeleton and all section blocks from sections/ directory."""
        if self._loaded:
            return

        skeleton_path = SECTIONS_DIR / "_skeleton.html"
        if skeleton_path.exists():
            self._skeleton = skeleton_path.read_text()
        else:
            logger.error("composer.missing_skeleton", path=str(skeleton_path))
            raise FileNotFoundError(f"Missing skeleton: {skeleton_path}")

        for html_file in sorted(SECTIONS_DIR.glob("*.html")):
            if html_file.name.startswith("_"):
                continue  # Skip skeleton and other private files
            block_id = html_file.stem
            html = html_file.read_text()
            slots = _extract_slots_from_html(html, block_id)
            self._sections[block_id] = SectionBlock(
                block_id=block_id,
                display_name=block_id.replace("_", " ").title(),
                html=html,
                slot_definitions=tuple(slots),
                has_mso_wrapper="<!--[if mso]>" in html,
                dark_mode_classes=_extract_dark_mode_classes(html),
            )

        self._loaded = True
        logger.info("composer.loaded", section_count=len(self._sections))

    def available_sections(self) -> list[str]:
        """Return list of available section block IDs."""
        self._ensure_loaded()
        return list(self._sections.keys())

    def get_section(self, block_id: str) -> SectionBlock | None:
        """Get a specific section block by ID."""
        self._ensure_loaded()
        return self._sections.get(block_id)

    def compose(self, section_names: list[str]) -> GoldenTemplate:
        """Assemble a new template from ordered section blocks.

        Args:
            section_names: Ordered list of section block IDs.

        Returns:
            GoldenTemplate with composed HTML, merged slots, and metadata.

        Raises:
            CompositionError: If any section_name is unknown or list is empty.
        """
        self._ensure_loaded()

        if not section_names:
            raise CompositionError("Cannot compose template with empty section list")

        # Validate all section names
        unknown = [s for s in section_names if s not in self._sections]
        if unknown:
            raise CompositionError(
                f"Unknown section blocks: {unknown}. Available: {self.available_sections()}"
            )

        # Build body content by concatenating section blocks
        sections_html_parts: list[str] = []
        all_slots: list[TemplateSlot] = []
        all_dark_mode_classes: set[str] = set()

        for name in section_names:
            block = self._sections[name]
            sections_html_parts.append(
                f"      <!-- Section: {block.display_name} -->\n{_indent(block.html, 6)}"
            )
            all_slots.extend(block.slot_definitions)
            all_dark_mode_classes.update(block.dark_mode_classes)

        sections_html = "\n".join(sections_html_parts)

        # Inject section blocks into skeleton
        html = self._skeleton.replace("{{SECTIONS}}", sections_html)

        # Merge dark mode CSS classes if needed
        if all_dark_mode_classes:
            dark_mode_css = _build_dark_mode_css(all_dark_mode_classes)
            html = html.replace("{{DARK_MODE_CSS}}", dark_mode_css)
        else:
            html = html.replace("{{DARK_MODE_CSS}}", "")

        metadata = TemplateMetadata(
            name="__compose__",
            display_name=f"Composed: {' + '.join(section_names)}",
            layout_type="promotional",
            column_count=_infer_column_count(section_names),
            has_hero_image=any(s.startswith("hero_image") for s in section_names),
            has_navigation="navigation" in section_names,
            has_social_links="social_links" in section_names,
            sections=tuple(section_names),
            ideal_for=("custom layout", "novel brief"),
            description="Dynamically composed template from section blocks.",
        )

        return GoldenTemplate(
            metadata=metadata,
            html=html,
            slots=tuple(all_slots),
        )

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()


class CompositionError(Exception):
    """Raised when template composition fails."""


# ── Private helpers ──


def _extract_slots_from_html(html: str, block_id: str) -> list[TemplateSlot]:  # noqa: ARG001
    """Extract data-slot markers from section HTML. Deduplicates by slot_id."""
    seen: set[str] = set()
    slots: list[TemplateSlot] = []
    for match in re.finditer(r'data-slot=["\']([^"\']+)["\']', html):
        slot_id = match.group(1)
        if slot_id in seen:
            continue
        seen.add(slot_id)
        slot_type = _infer_slot_type(slot_id)
        slots.append(
            TemplateSlot(
                slot_id=slot_id,
                slot_type=slot_type,
                selector=f"[data-slot='{slot_id}']",
                required=slot_type in ("headline", "cta", "body"),
                max_chars=_default_max_chars(slot_type),
                placeholder="",
            )
        )
    return slots


def _infer_slot_type(slot_id: str) -> SlotType:
    """Infer SlotType from slot_id naming convention."""
    if "headline" in slot_id or "title" in slot_id:
        return "headline"
    if "subheadline" in slot_id or "subtitle" in slot_id:
        return "subheadline"
    if "image" in slot_id or "img" in slot_id:
        return "image"
    if "cta" in slot_id and "url" in slot_id:
        return "cta"
    if "cta" in slot_id:
        return "cta"
    if "preheader" in slot_id:
        return "preheader"
    if "footer" in slot_id:
        return "footer"
    if "nav" in slot_id:
        return "nav"
    if "social" in slot_id:
        return "social"
    return "body"


def _default_max_chars(slot_type: str) -> int | None:
    """Return sensible max_chars defaults per slot type."""
    defaults: dict[str, int] = {
        "headline": 80,
        "subheadline": 120,
        "cta": 30,
        "preheader": 100,
    }
    return defaults.get(slot_type)


def _extract_dark_mode_classes(html: str) -> tuple[str, ...]:
    """Extract dark mode CSS class names from HTML."""
    classes: set[str] = set()
    for match in re.finditer(r'class="([^"]*)"', html):
        for cls in match.group(1).split():
            if cls.startswith("dark-"):
                classes.add(cls)
    return tuple(sorted(classes))


def _build_dark_mode_css(classes: set[str]) -> str:
    """Build dark mode CSS block for given class names."""
    css_map: dict[str, str] = {
        "dark-bg": "background-color: #1a1a2e !important;",
        "dark-text": "color: #e5e5e5 !important;",
    }
    rules: list[str] = []
    for cls in sorted(classes):
        if cls in css_map:
            rules.append(f"      .{cls} {{ {css_map[cls]} }}")

    if not rules:
        return ""

    media_rules = "\n".join(rules)
    outlook_rules_parts: list[str] = []
    for cls in sorted(classes):
        if cls in css_map:
            outlook_rules_parts.append(f"    [data-ogsc] .{cls} {{ {css_map[cls]} }}")
    outlook_rules = "\n".join(outlook_rules_parts)
    return f"""
    @media (prefers-color-scheme: dark) {{
{media_rules}
    }}
{outlook_rules}"""


def _indent(html: str, spaces: int) -> str:
    """Indent each line of HTML by N spaces."""
    prefix = " " * spaces
    return "\n".join(prefix + line if line.strip() else line for line in html.splitlines())


def _infer_column_count(section_names: list[str]) -> int:
    """Infer column count from section block names."""
    for name in section_names:
        if "3col" in name:
            return 3
        if "2col" in name:
            return 2
    return 1


# ── Module-level singleton ──

_composer: TemplateComposer | None = None


def get_composer() -> TemplateComposer:
    """Get or create the global TemplateComposer singleton."""
    global _composer
    if _composer is None:
        _composer = TemplateComposer()
    return _composer
