"""TreeBuilder — deterministic EmailTree assembly from tree-mode pipeline outputs.

Transforms 3-pass outputs (component selections, slot fills, design tokens)
into a validated EmailTree. Part of Phase 48.7 scaffolder tree mode.
"""

from __future__ import annotations

import dataclasses
from functools import lru_cache
from typing import Any

from app.components.tree_schema import (
    ButtonSlot,
    EmailTree,
    HtmlSlot,
    ImageSlot,
    TextSlot,
    TreeMetadata,
    TreeSection,
    validate_tree_against_manifest,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# Image file extensions for heuristic slot type inference
_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")


@dataclasses.dataclass(frozen=True)
class ComponentSelection:
    """LLM's component choice for a single email section."""

    component_slug: str
    rationale: str = ""


def _infer_slot_value(
    slot_id: str,
    content: str | dict[str, Any],
    slot_type: str,
) -> TextSlot | ImageSlot | ButtonSlot | HtmlSlot:
    """Map raw content to a typed SlotValue based on slot_type and content heuristics."""
    # If content is already a dict with a 'type' field, parse directly
    if isinstance(content, dict):
        slot_kind = str(content.get("type", "text"))
        if slot_kind == "button":
            return ButtonSlot(
                text=str(content.get("text", slot_id)),
                href=str(content.get("href", "#")),
                bg_color=str(content.get("bg_color", "#000000")),
                text_color=str(content.get("text_color", "#FFFFFF")),
            )
        if slot_kind == "image":
            return ImageSlot(
                src=str(content.get("src", "")),
                alt=str(content.get("alt", "")),
                width=int(content.get("width", 600)),
                height=int(content.get("height", 300)),
            )
        if slot_kind == "html":
            return HtmlSlot(html=str(content.get("html", "")))
        return TextSlot(text=str(content.get("text", "")))

    # String content — infer from slot_type and content heuristics
    text = str(content)

    if slot_type == "cta" or (slot_type == "content" and "href" in text.lower()):
        return ButtonSlot(
            text=text,
            href="#",
            bg_color="#000000",
            text_color="#FFFFFF",
        )

    if slot_type == "image" or any(text.lower().endswith(ext) for ext in _IMAGE_EXTENSIONS):
        return ImageSlot(
            src=text,
            alt=slot_id.replace("_", " "),
            width=600,
            height=300,
        )

    if "<" in text and ">" in text:
        return HtmlSlot(html=text)

    return TextSlot(text=text)


@lru_cache(maxsize=1)
def _build_manifest_index() -> tuple[frozenset[str], dict[str, list[dict[str, Any]]]]:
    """Build manifest index: (slugs, {slug: slot_definitions}).

    Cached at module level — manifest is static at runtime.
    """
    from app.components.data.seeds import COMPONENT_SEEDS

    slugs: set[str] = set()
    slot_defs: dict[str, list[dict[str, Any]]] = {}

    for seed in COMPONENT_SEEDS:
        slug = seed["slug"]
        slugs.add(slug)
        slot_defs[slug] = seed.get("slot_definitions", [])

    return frozenset(slugs), slot_defs


class TreeBuilder:
    """Assemble EmailTree from tree-mode pipeline outputs."""

    def __init__(
        self,
        manifest_slugs: set[str] | frozenset[str] | None = None,
        slot_definitions: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        if manifest_slugs is None or slot_definitions is None:
            cached_slugs, cached_defs = _build_manifest_index()
            self._manifest_slugs: set[str] | frozenset[str] = manifest_slugs or cached_slugs
            self._slot_definitions = slot_definitions or cached_defs
        else:
            self._manifest_slugs = manifest_slugs
            self._slot_definitions = slot_definitions

    def build(
        self,
        component_selections: list[ComponentSelection],
        slot_fills_by_section: dict[int, dict[str, TextSlot | ImageSlot | ButtonSlot | HtmlSlot]],
        design_tokens: dict[str, dict[str, str]],
        subject: str,
        preheader: str,
    ) -> EmailTree:
        """Build EmailTree from 3-pass outputs. Validates against manifest."""
        sections: list[TreeSection] = []

        for i, selection in enumerate(component_selections):
            slug = selection.component_slug
            fills = slot_fills_by_section.get(i, {})

            # Fall back to __custom__ for unknown slugs
            if slug != "__custom__" and slug not in self._manifest_slugs:
                logger.warning(
                    "scaffolder.tree_builder.unknown_slug",
                    slug=slug,
                    index=i,
                    fallback="__custom__",
                )
                sections.append(
                    TreeSection(
                        component_slug="__custom__",
                        slot_fills=fills,
                        custom_html=f"<!-- unknown component: {slug} -->",
                    )
                )
                continue

            sections.append(
                TreeSection(
                    component_slug=slug,
                    slot_fills=fills,
                )
            )

        tree = EmailTree(
            metadata=TreeMetadata(
                subject=subject or "Untitled",
                preheader=preheader,
                design_tokens=design_tokens,
            ),
            sections=sections,
        )

        # Validate against manifest
        slot_name_map: dict[str, list[str]] = {
            slug: [s.get("slot_id", "") for s in defs]
            for slug, defs in self._slot_definitions.items()
        }
        errors = validate_tree_against_manifest(
            tree,
            set(self._manifest_slugs),
            slot_name_map,
        )
        if errors:
            logger.warning(
                "scaffolder.tree_builder.validation_errors",
                error_count=len(errors),
                errors=errors[:5],
            )

        return tree
