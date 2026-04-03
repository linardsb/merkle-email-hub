"""Custom component generation via Scaffolder for low-confidence matches (Phase 47.8).

When ``ComponentMatch.confidence`` falls below the configured threshold, this
module generates a one-off email-safe HTML section using the Scaffolder agent
instead of rendering a poorly-matched template.
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.design_sync.figma.layout_analyzer import EmailSection
    from app.design_sync.protocol import ExtractedTokens

logger = get_logger(__name__)


def _build_brief(section: EmailSection) -> str:
    """Build a Scaffolder brief from section metadata."""
    parts: list[str] = [
        f"Generate a single email section of type '{section.section_type.value}'.",
        f"Column layout: {section.column_layout.value} ({section.column_count} columns).",
    ]

    if section.texts:
        snippets = [t.content[:80] for t in section.texts[:5]]
        parts.append(f"Text content ({len(section.texts)} blocks): {'; '.join(snippets)}")

    if section.images:
        parts.append(f"Image placeholders: {len(section.images)}")

    if section.buttons:
        labels = [b.text for b in section.buttons[:3]]
        parts.append(f"Buttons: {', '.join(labels)}")

    parts.append(
        "Requirements: table-based layout (table/tr/td), inline styles only. "
        "No div or p tags for layout. Must be a single email section, not a full email."
    )

    return " ".join(parts)


def _build_design_context(
    tokens: ExtractedTokens,
    design_screenshot: bytes | None = None,
) -> dict[str, object]:
    """Build design context dict for the Scaffolder from extracted tokens."""
    design_tokens: dict[str, object] = {}

    if tokens.colors:
        design_tokens["colors"] = [
            {"name": c.name, "hex": c.hex, "opacity": c.opacity} for c in tokens.colors
        ]

    if tokens.typography:
        design_tokens["typography"] = [
            {
                "name": t.name,
                "family": t.family,
                "weight": t.weight,
                "size": t.size,
            }
            for t in tokens.typography
        ]

    if tokens.spacing:
        design_tokens["spacing"] = [{"name": s.name, "value": s.value} for s in tokens.spacing]

    context: dict[str, object] = {"design_tokens": design_tokens}

    if design_screenshot is not None:
        context["design_screenshot_b64"] = base64.b64encode(design_screenshot).decode("ascii")

    return context


async def generate_custom_component(
    section: EmailSection,
    tokens: ExtractedTokens,
    *,
    design_screenshot: bytes | None = None,
) -> str:
    """Generate a custom email section via the Scaffolder agent.

    Args:
        section: The email section to generate HTML for.
        tokens: Extracted design tokens (colors, typography, spacing).
        design_screenshot: Optional screenshot of the design section.

    Returns:
        Generated HTML string for the section.

    Raises:
        Exception: Propagated from the Scaffolder service on failure.
    """
    from app.ai.agents.scaffolder.schemas import ScaffolderRequest
    from app.ai.agents.scaffolder.service import get_scaffolder_service
    from app.ai.security.prompt_guard import scan_for_injection

    brief = _build_brief(section)

    # Scan brief for prompt injection (section text comes from Figma API)
    scan_result = scan_for_injection(brief)
    if not scan_result.clean:
        logger.warning(
            "design_sync.custom_component_injection_detected",
            flags=scan_result.flags,
        )
        if scan_result.sanitized is not None:
            brief = scan_result.sanitized

    design_context = _build_design_context(tokens, design_screenshot)

    settings = get_settings()
    model_override = settings.design_sync.custom_component_model

    request = ScaffolderRequest(
        brief=brief,
        run_qa=False,
        output_mode="html",
        design_context=design_context,
    )

    # Apply model override if configured
    if model_override:
        request.brand_config = {"model_override": model_override}

    service = get_scaffolder_service()
    response = await service.generate(request)

    logger.info(
        "design_sync.custom_component_generated",
        section_type=section.section_type.value,
        model=response.model,
    )

    return response.html
