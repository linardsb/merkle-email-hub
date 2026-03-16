"""Visual defect correction service — LLM-based HTML fixes for VLM-detected defects."""

from __future__ import annotations

from app.ai.agents.visual_qa.decisions import DetectedDefect
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import extract_html, sanitize_html_xss
from app.core.config import get_settings
from app.core.logging import get_logger
from app.knowledge.ontology.registry import load_ontology

logger = get_logger(__name__)

CORRECTION_SYSTEM_PROMPT = (
    "You are an email HTML developer specializing in cross-client rendering fixes. "
    "Apply the requested fixes while preserving all existing HTML structure and functionality. "
    "Return ONLY the corrected HTML — no explanations."
)

_HTML_CAP = 100_000


async def correct_visual_defects(
    html: str,
    defects: tuple[DetectedDefect, ...],
    model: str,
) -> tuple[str, list[str]]:
    """Apply LLM-based corrections for VLM-detected visual defects.

    Args:
        html: Original email HTML.
        defects: Detected defects from VisualQAService.
        model: LLM model identifier for correction.

    Returns:
        Tuple of (corrected_html, list_of_corrections_applied).
        If no fixable defects or LLM fails, returns (html, []) with zero cost.
    """
    # Filter to fixable defects only (have css_property or suggested_fix)
    fixable = [d for d in defects if d.css_property or d.suggested_fix]
    if not fixable:
        return html, []

    # Build correction instructions with ontology fallbacks
    onto = load_ontology()
    instructions: list[str] = []
    corrections_attempted: list[str] = []

    for defect in fixable:
        parts: list[str] = [
            f"- **{defect.region}** ({defect.severity}): {defect.description}",
            f"  Affected clients: {', '.join(defect.affected_clients)}",
        ]

        # Try ontology fallback if css_property is set
        fallback_code: str | None = None
        if defect.css_property:
            prop = onto.find_property_by_name(defect.css_property)
            if prop:
                fallbacks = onto.fallbacks_for(prop.id)
                if fallbacks:
                    fb = fallbacks[0]
                    parts.append(f"  Known fallback technique: {fb.technique}")
                    parts.append(f"  Replacement code:\n```\n{fb.code_example}\n```")
                    fallback_code = fb.technique

        # Include VLM's suggested fix when no ontology fallback
        if not fallback_code and defect.suggested_fix:
            parts.append(f"  Suggested fix: {defect.suggested_fix}")

        instructions.append("\n".join(parts))
        corrections_attempted.append(f"{defect.region}:{defect.css_property or 'visual'}")

    # Build correction prompt
    capped_html = html[:_HTML_CAP] if len(html) > _HTML_CAP else html
    correction_prompt = (
        "Fix the following rendering defects detected in this HTML email. "
        "Apply the provided fallback techniques where available. "
        "For defects without a known fallback, use the suggested fix. "
        "Preserve all other HTML exactly as-is. Return ONLY the corrected HTML.\n\n"
        + "\n\n".join(instructions)
        + "\n\nOriginal HTML:\n```html\n"
        + capped_html
        + "\n```"
    )

    logger.info(
        "visual_qa.correction.started",
        fixable_defects=len(fixable),
        html_length=len(html),
    )

    # Call LLM
    settings = get_settings()
    provider_name = settings.ai.provider
    registry = get_registry()
    provider = registry.get_llm(provider_name)

    messages = [
        Message(role="system", content=sanitize_prompt(CORRECTION_SYSTEM_PROMPT)),
        Message(role="user", content=sanitize_prompt(correction_prompt)),
    ]

    try:
        result = await provider.complete(messages, model_override=model, max_tokens=16_384)
    except Exception:
        logger.warning("visual_qa.correction.llm_failed", exc_info=True)
        return html, []  # Failure-safe: return original

    # Validate and sanitize output
    raw = validate_output(result.content)
    corrected = extract_html(raw)
    corrected = sanitize_html_xss(corrected)

    if not corrected or len(corrected) < 50:
        logger.warning(
            "visual_qa.correction.output_too_short",
            length=len(corrected) if corrected else 0,
        )
        return html, []  # Failure-safe: return original

    logger.info(
        "visual_qa.correction.applied",
        corrections=corrections_attempted,
        original_length=len(html),
        corrected_length=len(corrected),
    )

    return corrected, corrections_attempted
