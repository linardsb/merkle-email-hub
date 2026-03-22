"""Template registry — loads, indexes, and serves golden templates."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from app.projects.template_config import ProjectTemplateConfig

from app.ai.templates.models import (
    DefaultTokens,
    GoldenTemplate,
    LayoutType,
    TemplateMetadata,
    TemplateSlot,
)
from app.ai.templates.precompiler import PrecompilationReport, TemplatePrecompiler
from app.core.logging import get_logger

logger = get_logger(__name__)

LIBRARY_DIR = Path(__file__).parent / "library"
METADATA_DIR = LIBRARY_DIR / "_metadata"
MAIZZLE_SRC_DIR = Path(__file__).parent / "maizzle_src"


class TemplateRegistry:
    """Loads, indexes, and serves golden templates."""

    def __init__(self) -> None:
        self._templates: dict[str, GoldenTemplate] = {}
        self._loaded = False

    def load(self) -> None:
        """Load all templates from library/ directory."""
        if self._loaded:
            return

        for html_file in sorted(LIBRARY_DIR.glob("*.html")):
            name = html_file.stem
            metadata_file = METADATA_DIR / f"{name}.yaml"
            if not metadata_file.exists():
                logger.warning("templates.missing_metadata", template=name)
                continue

            html = html_file.read_text()
            metadata_raw = yaml.safe_load(metadata_file.read_text())
            metadata = _parse_metadata(metadata_raw)
            slots = _parse_slots(metadata_raw.get("slots", []))

            maizzle_src = ""
            src_file = MAIZZLE_SRC_DIR / f"{name}.html"
            if src_file.exists():
                maizzle_src = src_file.read_text()

            default_tokens = _parse_default_tokens(metadata_raw.get("default_tokens"))

            self._templates[name] = GoldenTemplate(
                metadata=metadata,
                html=html,
                slots=slots,
                maizzle_source=maizzle_src,
                default_tokens=default_tokens,
            )

        self._loaded = True

        # Pre-compile CSS for all templates (26.3)
        try:
            precompiler = TemplatePrecompiler()
            self._templates, report = precompiler.precompile_all(self._templates)
            logger.info(
                "templates.registry_precompiled",
                succeeded=report.succeeded,
                failed=report.failed,
                total_reduction_bytes=report.total_size_reduction_bytes,
            )
        except Exception:
            logger.warning("templates.registry_precompile_failed", exc_info=True)
            # Non-fatal — templates work without precompilation

        logger.info("templates.registry_loaded", count=len(self._templates))

    def get(self, name: str) -> GoldenTemplate | None:
        """Get template by name."""
        self._ensure_loaded()
        return self._templates.get(name)

    def search(
        self,
        layout_type: LayoutType | None = None,
        column_count: int | None = None,
        has_hero: bool | None = None,
    ) -> list[GoldenTemplate]:
        """Filter templates by criteria."""
        self._ensure_loaded()
        results = list(self._templates.values())
        if layout_type is not None:
            results = [t for t in results if t.metadata.layout_type == layout_type]
        if column_count is not None:
            results = [t for t in results if t.metadata.column_count == column_count]
        if has_hero is not None:
            results = [t for t in results if t.metadata.has_hero_image == has_hero]
        return results

    def list_for_selection(self) -> list[TemplateMetadata]:
        """Return metadata-only list for LLM template selection prompt."""
        self._ensure_loaded()
        return [t.metadata for t in self._templates.values()]

    def fill_slots(self, template: GoldenTemplate, fills: dict[str, str]) -> str:
        """Replace slot placeholder content with fills.

        Uses data-slot attributes to locate slots in the HTML DOM.
        For URL-type slots (on <a>/<img> tags), replaces href/src attributes.
        For content slots, replaces inner content.
        Processes inner (non-URL) slots first to avoid clobbering nested elements.
        """
        html = template.html

        # Process inner content slots first, then URL/attribute slots
        content_slots = [s for s in template.slots if not _is_url_slot(s)]
        url_slots = [s for s in template.slots if _is_url_slot(s)]

        for slot in content_slots + url_slots:
            if slot.slot_id not in fills:
                continue
            fill_content = fills[slot.slot_id]
            if slot.max_chars and len(fill_content) > slot.max_chars:
                fill_content = fill_content[: slot.max_chars]

            if _is_url_slot(slot):
                html = _fill_url_slot(html, slot.slot_id, fill_content)
            else:
                html = _fill_content_slot(html, slot.slot_id, fill_content)
        return html

    def get_for_project(
        self,
        template_config: ProjectTemplateConfig | None,
    ) -> list[GoldenTemplate]:
        """Return templates filtered per project config.

        1. Load global golden templates
        2. Remove disabled_templates
        3. Prepend preferred_templates (move to front)

        Composition-time concerns (custom sections, section overrides, design
        token application) are handled by 11.25.4 pipeline integration.
        """
        self._ensure_loaded()

        if template_config is None:
            return list(self._templates.values())

        disabled = set(template_config.disabled_templates)
        templates = {name: t for name, t in self._templates.items() if name not in disabled}

        preferred = list(template_config.preferred_templates)
        preferred_templates = [templates.pop(name) for name in preferred if name in templates]
        remaining = list(templates.values())

        return preferred_templates + remaining

    def list_for_selection_scoped(
        self,
        template_config: ProjectTemplateConfig | None,
    ) -> list[TemplateMetadata]:
        """Return metadata list filtered per project config, with preferred templates marked.

        Used to build the LLM's template selection prompt.
        """
        templates = self.get_for_project(template_config)
        preferred_names = set(template_config.preferred_templates if template_config else ())

        result: list[TemplateMetadata] = []
        for t in templates:
            if t.metadata.name in preferred_names:
                result.append(
                    TemplateMetadata(
                        name=t.metadata.name,
                        display_name=t.metadata.display_name,
                        layout_type=t.metadata.layout_type,
                        column_count=t.metadata.column_count,
                        has_hero_image=t.metadata.has_hero_image,
                        has_navigation=t.metadata.has_navigation,
                        has_social_links=t.metadata.has_social_links,
                        sections=t.metadata.sections,
                        ideal_for=t.metadata.ideal_for,
                        description=f"[RECOMMENDED] {t.metadata.description}",
                    )
                )
            else:
                result.append(t.metadata)
        return result

    def register_uploaded(self, template: GoldenTemplate) -> None:
        """Register a template from the upload pipeline.

        Validates name uniqueness and stores in the in-memory registry.
        Does NOT persist to disk (DB is source of truth for uploaded templates).

        Raises:
            ValueError: If a template with the same name already exists.
        """
        self._ensure_loaded()
        name = template.metadata.name
        if name in self._templates:
            msg = f"Template '{name}' already exists in registry"
            raise ValueError(msg)

        # Pre-compile CSS for uploaded template (26.3)
        try:
            precompiler = TemplatePrecompiler()
            template = precompiler.precompile(template)
        except Exception:
            logger.warning(
                "templates.uploaded_precompile_failed",
                name=name,
                exc_info=True,
            )
            # Non-fatal — template works without precompilation

        self._templates[name] = template
        logger.info("templates.uploaded_registered", name=name)

    def list_for_selection_with_uploaded(
        self,
        project_id: int | None = None,
    ) -> list[TemplateMetadata]:
        """List all templates for LLM selection, including uploaded ones.

        Uploaded templates for the given project are tagged with [uploaded].
        """
        self._ensure_loaded()
        result: list[TemplateMetadata] = []
        for t in self._templates.values():
            if t.source == "uploaded":
                # Only include uploaded templates that match the project scope
                if t.project_id is not None and t.project_id != project_id:
                    continue
                result.append(
                    TemplateMetadata(
                        name=t.metadata.name,
                        display_name=t.metadata.display_name,
                        layout_type=t.metadata.layout_type,
                        column_count=t.metadata.column_count,
                        has_hero_image=t.metadata.has_hero_image,
                        has_navigation=t.metadata.has_navigation,
                        has_social_links=t.metadata.has_social_links,
                        sections=t.metadata.sections,
                        ideal_for=t.metadata.ideal_for,
                        description=f"[uploaded] {t.metadata.description}",
                    )
                )
            else:
                result.append(t.metadata)
        return result

    def precompile_all(
        self,
        target_clients: tuple[str, ...] | None = None,
    ) -> PrecompilationReport:
        """Re-precompile all templates. Used by admin endpoint."""
        self._ensure_loaded()
        precompiler = TemplatePrecompiler(target_clients=target_clients)
        self._templates, report = precompiler.precompile_all(self._templates)
        return report

    def names(self) -> list[str]:
        """Return all template names."""
        self._ensure_loaded()
        return list(self._templates.keys())

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()


def _is_url_slot(slot: TemplateSlot) -> bool:
    """Check if a slot targets an attribute (href/src) rather than inner content."""
    return slot.slot_id.endswith("_url") or slot.slot_type == "image"


def _fill_content_slot(html: str, slot_id: str, content: str) -> str:
    """Replace inner content of element with data-slot matching slot_id.

    Extracts the tag name from the opening tag and matches the corresponding
    closing tag, correctly handling nested elements. Uses lambda replacement
    to avoid re.escape issues in replacement strings.
    """
    # Match opening tag with data-slot, capture the tag name for closing match
    pattern = re.compile(
        r"(<(\w+)\b[^>]*\bdata-slot=[\"']" + re.escape(slot_id) + r"[\"'][^>]*>)(.*?)(</\2>)",
        re.DOTALL,
    )
    return pattern.sub(lambda m: m.group(1) + content + m.group(4), html, count=1)


def _fill_url_slot(html: str, slot_id: str, value: str) -> str:
    """Replace href or src attribute on element with data-slot matching slot_id.

    Uses lambda replacement to avoid re.escape issues in replacement strings.
    """
    if slot_id.endswith("_image") or slot_id.endswith("_img"):
        attr = "src"
    else:
        attr = "href"
    pattern = re.compile(
        r"""(<[^>]+data-slot=["']"""
        + re.escape(slot_id)
        + r"""["'][^>]*\s)"""
        + attr
        + r"""=["'][^"']*["']""",
    )
    return pattern.sub(lambda m: m.group(1) + f'{attr}="{value}"', html, count=1)


def _parse_metadata(raw: dict[str, object]) -> TemplateMetadata:
    """Parse YAML metadata dict into TemplateMetadata."""
    return TemplateMetadata(
        name=str(raw["name"]),
        display_name=str(raw["display_name"]),
        layout_type=str(raw["layout_type"]),  # type: ignore[arg-type]
        column_count=int(raw.get("column_count", 1)),  # type: ignore[call-overload]
        has_hero_image=bool(raw.get("has_hero_image", False)),
        has_navigation=bool(raw.get("has_navigation", False)),
        has_social_links=bool(raw.get("has_social_links", False)),
        sections=tuple(raw.get("sections", [])),  # type: ignore[arg-type]
        ideal_for=tuple(raw.get("ideal_for", [])),  # type: ignore[arg-type]
        description=str(raw.get("description", "")),
    )


def _parse_default_tokens(raw: object) -> DefaultTokens | None:
    """Parse default_tokens from YAML metadata."""
    if not raw or not isinstance(raw, dict):
        return None

    def _str_dict(key: str) -> dict[str, str]:
        val = raw.get(key, {})  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
        if not isinstance(val, dict):
            return {}
        return {str(k): str(v) for k, v in val.items()}  # pyright: ignore[reportUnknownVariableType,reportUnknownArgumentType,reportUnknownMemberType]

    return DefaultTokens(
        colors=_str_dict("colors"),
        fonts=_str_dict("fonts"),
        font_sizes=_str_dict("font_sizes"),
        spacing=_str_dict("spacing"),
    )


def _parse_slots(raw_slots: list[dict[str, object]]) -> tuple[TemplateSlot, ...]:
    """Parse YAML slot definitions into TemplateSlot tuple."""
    slots: list[TemplateSlot] = []
    for s in raw_slots:
        slots.append(
            TemplateSlot(
                slot_id=str(s["slot_id"]),
                slot_type=str(s["slot_type"]),  # type: ignore[arg-type]
                selector=str(s["selector"]),
                required=bool(s.get("required", True)),
                max_chars=int(s["max_chars"]) if s.get("max_chars") else None,  # type: ignore[call-overload]
                placeholder=str(s.get("placeholder", "")),
            )
        )
    return tuple(slots)


_registry: TemplateRegistry | None = None


def get_template_registry() -> TemplateRegistry:
    """Get or create the global template registry singleton."""
    global _registry
    if _registry is None:
        _registry = TemplateRegistry()
    return _registry
