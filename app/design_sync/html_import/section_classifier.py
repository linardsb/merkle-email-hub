"""Heuristic section type classification with AI fallback bridge."""

from __future__ import annotations

import re
from dataclasses import replace
from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.design_sync.email_design_document import (
    DocumentButton,
    DocumentImage,
    DocumentSection,
    DocumentText,
)

logger = get_logger(__name__)

if TYPE_CHECKING:
    from app.design_sync.figma.layout_analyzer import EmailSection

_SOCIAL_URL_RE = re.compile(
    r"facebook|twitter|x\.com|linkedin|instagram|youtube",
    re.IGNORECASE,
)
_UNSUBSCRIBE_RE = re.compile(r"unsubscribe|opt.out|manage.preferences", re.IGNORECASE)
_COPYRIGHT_RE = re.compile(r"©|\bcopyright\b|\(c\)", re.IGNORECASE)
_LEGAL_RE = re.compile(
    r"privacy\s*policy|terms\s*(of|&)\s*(service|use)|all\s*rights\s*reserved",
    re.IGNORECASE,
)


def classify_sections(
    sections: list[DocumentSection],
    *,
    container_position_map: dict[str, float] | None = None,
) -> list[DocumentSection]:
    """Apply heuristic rules to classify UNKNOWN sections.

    Returns a new list with updated ``type`` fields.

    Rules (first match wins per section):
    1. ``data-section-type`` already set → keep
    2. First section with logo image (small img, < 200px height) → HEADER
    3. Large heading (> 24px) + optional button → HERO
    4. Only button(s), no body text → CTA
    5. Social media URLs → SOCIAL
    6. No content, spacer-like → SPACER
    7. Last section with "unsubscribe" / "©" → FOOTER
    8. Bottom 20% with small text → FOOTER
    9. Remaining with text → CONTENT
    """
    if not sections:
        return []

    # Build position map if not provided
    if container_position_map is None:
        total_height = sum(s.height or 50.0 for s in sections)
        if total_height <= 0:
            total_height = len(sections) * 50.0
        cumulative = 0.0
        container_position_map = {}
        for s in sections:
            container_position_map[s.id] = cumulative / total_height
            cumulative += s.height or 50.0

    result: list[DocumentSection] = []
    for idx, section in enumerate(sections):
        if section.type != "unknown":
            result.append(section)
            continue

        classified_type = _classify_single(
            section,
            idx=idx,
            total=len(sections),
            position=container_position_map.get(section.id, 0.5),
        )
        result.append(replace(section, type=classified_type))

    return result


def _classify_single(
    section: DocumentSection,
    *,
    idx: int,
    total: int,
    position: float,
) -> str:
    """Classify a single section using heuristics."""
    all_texts = _all_texts(section)
    all_images = _all_images(section)
    all_buttons = _all_buttons(section)
    combined_text = " ".join(t.content for t in all_texts)

    # Rule 2: First section with small image → HEADER
    if idx == 0 and all_images and not any(t.is_heading for t in all_texts):
        max_img_height = max((img.height or 0.0) for img in all_images)
        if max_img_height < 200.0 or max_img_height == 0.0:
            return "header"

    # Rule 3: Large heading → HERO
    has_large_heading = any(t.is_heading and (t.font_size or 0) > 24.0 for t in all_texts)
    if has_large_heading:
        return "hero"

    # Rule 4: Only buttons, no body text → CTA
    body_texts = [t for t in all_texts if not t.is_heading]
    if all_buttons and not body_texts:
        return "cta"

    # Rule 5: Social media URLs
    if _SOCIAL_URL_RE.search(combined_text):
        return "social"

    # Rule 6: No content → SPACER
    if not all_texts and not all_images and not all_buttons:
        return "spacer"

    # Rule 7: Last section with unsubscribe/copyright → FOOTER
    is_bottom = idx >= total - 2
    if is_bottom and (
        _UNSUBSCRIBE_RE.search(combined_text)
        or _COPYRIGHT_RE.search(combined_text)
        or _LEGAL_RE.search(combined_text)
    ):
        return "footer"

    # Rule 8: Bottom 20% with small text → FOOTER
    if position >= 0.8:
        avg_font_size = _avg_font_size(all_texts)
        if avg_font_size is not None and avg_font_size < 12.0:
            return "footer"

    # Rule 9: Default → CONTENT
    return "content"


async def classify_with_ai_fallback(
    sections: list[DocumentSection],
    *,
    container_position_map: dict[str, float] | None = None,
    ai_enabled: bool = True,
) -> list[DocumentSection]:
    """Classify sections: heuristics first, then AI for remaining UNKNOWN.

    1. Run ``classify_sections()`` (deterministic)
    2. Collect still-UNKNOWN sections
    3. If AI enabled, bridge to ``classify_sections_batch()`` + ``detect_content_roles()``
    4. Merge results back
    """
    classified = classify_sections(sections, container_position_map=container_position_map)

    if not ai_enabled:
        return classified

    unknown_indices = [i for i, s in enumerate(classified) if s.type == "unknown"]
    if not unknown_indices:
        # Still run content role detection on all sections
        return await _apply_content_roles(classified)

    # Bridge to AI classifiers
    from app.design_sync.ai_layout_classifier import classify_sections_batch

    # Convert to EmailSection for AI compatibility
    email_sections = [_bridge_to_email_section(classified[i]) for i in unknown_indices]
    all_types = list({s.type for s in classified if s.type != "unknown"})
    all_ids = [s.id for s in classified]

    try:
        ai_results = await classify_sections_batch(
            email_sections,
            all_section_types=all_types,
            all_node_ids=all_ids,
        )
    except Exception:
        logger.warning("design_sync.html_import.ai_classify_failed", exc_info=True)
        ai_results = []

    # Merge AI classifications
    result = list(classified)
    for j, orig_idx in enumerate(unknown_indices):
        if j < len(ai_results):
            ai_cls = ai_results[j]
            result[orig_idx] = replace(
                result[orig_idx],
                type=ai_cls.section_type,
                classification_confidence=ai_cls.confidence,
            )

    return await _apply_content_roles(result)


async def _apply_content_roles(
    sections: list[DocumentSection],
) -> list[DocumentSection]:
    """Run content role detection and merge results."""
    from app.design_sync.ai_content_detector import detect_content_roles

    email_sections = [_bridge_to_email_section(s) for s in sections]
    try:
        annotations = await detect_content_roles(email_sections)
    except Exception:
        logger.warning("design_sync.html_import.content_roles_failed", exc_info=True)
        return sections

    role_map: dict[str, list[str]] = {}
    for ann in annotations:
        role_map[ann.section_node_id] = list(ann.roles)

    result: list[DocumentSection] = []
    for s in sections:
        roles = role_map.get(s.id, [])
        if roles:
            result.append(replace(s, content_roles=roles))
        else:
            result.append(s)
    return result


def _bridge_to_email_section(doc_section: DocumentSection) -> EmailSection:
    """Convert ``DocumentSection`` → ``EmailSection`` for AI classifier compatibility."""
    return doc_section.to_email_section()


# ── Helpers ────────────────────────────────────────────────────────


def _all_texts(section: DocumentSection) -> list[DocumentText]:
    """Collect all texts including from columns."""
    texts = list(section.texts)
    for col in section.columns:
        texts.extend(col.texts)
    return texts


def _all_images(section: DocumentSection) -> list[DocumentImage]:
    """Collect all images including from columns."""
    images = list(section.images)
    for col in section.columns:
        images.extend(col.images)
    return images


def _all_buttons(section: DocumentSection) -> list[DocumentButton]:
    """Collect all buttons including from columns."""
    buttons = list(section.buttons)
    for col in section.columns:
        buttons.extend(col.buttons)
    return buttons


def _avg_font_size(texts: list[DocumentText]) -> float | None:
    """Average font size across text blocks."""
    sizes = [t.font_size for t in texts if t.font_size is not None]
    if not sizes:
        return None
    return sum(sizes) / len(sizes)
