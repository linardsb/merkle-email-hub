"""LLM-based section classification fallback for unclassified sections.

Called only when heuristic classification in layout_analyzer yields UNKNOWN.
Uses lightweight model (Haiku) with structured JSON output and caches results
by section content hash to avoid redundant LLM calls.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.design_sync.figma.layout_analyzer import (
        EmailSection,
    )

logger = get_logger(__name__)

# Module-level cache: section hash → classification result (bounded to prevent unbounded growth)
_CACHE_MAX_SIZE = 1024
_classification_cache: dict[str, SectionClassification] = {}

_CLASSIFICATION_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "section_type": {
            "type": "string",
            "enum": [
                "header",
                "preheader",
                "hero",
                "content",
                "cta",
                "footer",
                "social",
                "divider",
                "spacer",
                "nav",
                "unknown",
            ],
        },
        "column_layout": {
            "type": "string",
            "enum": ["single", "two-column", "three-column", "multi-column"],
        },
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "reasoning": {"type": "string", "maxLength": 200},
    },
    "required": ["section_type", "column_layout", "confidence", "reasoning"],
}


@dataclass(frozen=True)
class SectionClassification:
    """Result of AI-based section classification."""

    section_type: str
    column_layout: str
    confidence: float
    reasoning: str


def section_cache_key(section: EmailSection) -> str:
    """Compute a deterministic cache key from section structural properties."""
    parts = [
        section.node_name,
        str(section.width),
        str(section.height),
        str(len(section.texts)),
        str(len(section.images)),
        str(len(section.buttons)),
    ]
    for t in section.texts[:3]:
        parts.append(t.content[:50])
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _build_prompt(
    section: EmailSection,
    sibling_types: list[str],
    section_index: int,
    total_sections: int,
) -> str:
    """Build a compact structural prompt for section classification."""
    lines = [
        "Classify this email section. Respond with JSON only.",
        "",
        f"Section {section_index + 1} of {total_sections}:",
        f"  Name: {section.node_name}",
        f"  Dimensions: {section.width}x{section.height}",
    ]

    if section.bg_color:
        lines.append(f"  Background: {section.bg_color}")

    # Sibling context
    if section_index > 0:
        lines.append(f"  Previous section: {sibling_types[section_index - 1]}")
    if section_index < total_sections - 1:
        lines.append(f"  Next section: {sibling_types[section_index + 1]}")

    # Text content snippets
    if section.texts:
        lines.append(f"  Texts ({len(section.texts)}):")
        for t in section.texts[:5]:
            snippet = t.content[:100]
            size_info = f" (size={t.font_size})" if t.font_size else ""
            lines.append(f'    - "{snippet}"{size_info}')

    # Image summary
    if section.images:
        lines.append(f"  Images ({len(section.images)}):")
        for img in section.images[:3]:
            lines.append(f"    - {img.width}x{img.height}")

    # Button summary
    if section.buttons:
        lines.append(f"  Buttons ({len(section.buttons)}):")
        for btn in section.buttons[:3]:
            lines.append(f'    - "{btn.text}"')

    return "\n".join(lines)


def _parse_classification(raw: str) -> SectionClassification | None:
    """Parse LLM JSON response into a SectionClassification."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None

    from app.design_sync.figma.layout_analyzer import ColumnLayout, EmailSectionType

    section_type = data.get("section_type", "unknown")
    column_layout = data.get("column_layout", "single")
    confidence = data.get("confidence", 0.0)
    reasoning = data.get("reasoning", "")

    # Validate enum values
    try:
        EmailSectionType(section_type)
    except ValueError:
        section_type = "unknown"
        confidence = 0.0

    try:
        ColumnLayout(column_layout)
    except ValueError:
        column_layout = "single"

    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    confidence = max(0.0, min(1.0, float(confidence)))

    return SectionClassification(
        section_type=section_type,
        column_layout=column_layout,
        confidence=confidence,
        reasoning=str(reasoning)[:200],
    )


async def classify_sections_batch(
    sections: list[EmailSection],
    *,
    all_section_types: list[str],
    all_node_ids: list[str] | None = None,
) -> list[SectionClassification]:
    """Classify a batch of UNKNOWN sections using LLM fallback.

    Each section is classified independently with its own LLM call.
    Results are cached by section content hash.

    Args:
        sections: Sections with UNKNOWN type to classify.
        all_section_types: Types of ALL sections (for sibling context).
        all_node_ids: Node IDs of ALL sections (to find each section's index).

    Returns:
        Classifications in the same order as input sections.
    """
    from app.ai.protocols import Message
    from app.ai.registry import get_registry
    from app.ai.routing import resolve_model

    # Build node_id → index lookup for correct sibling context
    node_id_to_index: dict[str, int] = {}
    if all_node_ids:
        node_id_to_index = {nid: i for i, nid in enumerate(all_node_ids)}

    results: list[SectionClassification] = []
    model = resolve_model("lightweight")
    registry = get_registry()
    provider = registry.get_llm(model)

    for section in sections:
        cache_key = section_cache_key(section)

        # Check cache first
        if cache_key in _classification_cache:
            logger.debug(
                "design_sync.ai_classifier.cache_hit",
                node_id=section.node_id,
                cache_key=cache_key,
            )
            results.append(_classification_cache[cache_key])
            continue

        # Find this section's position in the full layout
        section_index = node_id_to_index.get(section.node_id, 0)

        prompt = _build_prompt(
            section,
            sibling_types=all_section_types,
            section_index=section_index,
            total_sections=len(all_section_types),
        )

        try:
            response = await provider.complete(
                [Message(role="user", content=prompt)],
                model=model,
            )

            classification = _parse_classification(response.content)
            if classification is None or classification.confidence < 0.3:
                classification = SectionClassification(
                    section_type="unknown",
                    column_layout="single",
                    confidence=0.0,
                    reasoning="LLM response could not be parsed or confidence too low",
                )

            if len(_classification_cache) >= _CACHE_MAX_SIZE:
                _classification_cache.clear()
            _classification_cache[cache_key] = classification
            logger.info(
                "design_sync.ai_classifier.classified",
                node_id=section.node_id,
                section_type=classification.section_type,
                confidence=classification.confidence,
            )

        except Exception:
            logger.warning(
                "design_sync.ai_classifier.llm_error",
                node_id=section.node_id,
                exc_info=True,
            )
            classification = SectionClassification(
                section_type="unknown",
                column_layout="single",
                confidence=0.0,
                reasoning="LLM call failed",
            )

        results.append(classification)

    return results


def clear_cache() -> None:
    """Clear the classification cache (for testing)."""
    _classification_cache.clear()
