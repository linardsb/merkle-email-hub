"""VLM-powered visual comparison service for section-by-section diff.

Phase 47.2: Compares Figma design screenshots against rendered HTML screenshots
using ODiff as a pre-filter and a vision-language model for structured correction
extraction. Enables the automatic correction loop in Phase 47.

Flow per section:
1. ODiff pixel diff — if below threshold, skip VLM (section is "good enough").
2. Check bounded cache — avoid duplicate VLM calls for identical image pairs.
3. VLM analysis — returns structured corrections (color, font, spacing, etc.).
4. Cache result.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.ai.multimodal import ContentBlock
    from app.design_sync.figma.layout_analyzer import EmailSection

logger = get_logger(__name__)

# Bounded cache: composite hash -> corrections list.
_CACHE_MAX_SIZE = 256
_vlm_cache: dict[str, list[SectionCorrection]] = {}

CorrectionType = Literal["color", "font", "spacing", "layout", "content", "image"]


@dataclass(frozen=True)
class SectionCorrection:
    """A single actionable correction for an HTML section."""

    node_id: str
    section_idx: int
    correction_type: CorrectionType
    css_selector: str
    css_property: str
    current_value: str
    correct_value: str
    confidence: float
    reasoning: str


@dataclass(frozen=True)
class VerificationResult:
    """Aggregated result of visual verification across all sections."""

    iteration: int
    fidelity_score: float  # 0.0-1.0 (fraction of sections converged)
    section_scores: dict[str, float]  # node_id -> per-section diff_percentage
    corrections: list[SectionCorrection]
    pixel_diff_pct: float  # weighted average across sections
    converged: bool  # True when corrections is empty


@dataclass(frozen=True)
class VerificationLoopResult:
    """Aggregated result of the iterative verification loop."""

    iterations: list[VerificationResult]
    final_html: str
    initial_fidelity: float
    final_fidelity: float
    total_corrections_applied: int
    total_vlm_cost_tokens: int
    converged: bool
    reverted: bool  # True if last iteration regressed and was reverted


def clear_verify_cache() -> None:
    """Clear the VLM verification cache (test helper)."""
    _vlm_cache.clear()


def _cache_key(figma_bytes: bytes, html_bytes: bytes) -> str:
    """Composite hash of both screenshots for cache keying."""
    h = hashlib.sha256(figma_bytes + html_bytes).hexdigest()[:16]
    return h


async def compare_sections(
    design_screenshots: dict[str, bytes],
    rendered_screenshots: dict[str, bytes],
    html: str,  # noqa: ARG001  Reserved for future context injection
    sections: list[EmailSection],
    *,
    iteration: int = 0,
    global_design_image: bytes | None = None,
) -> VerificationResult:
    """Compare Figma design screenshots against rendered HTML screenshots.

    For each section, runs ODiff first; if the diff exceeds the threshold,
    calls a VLM to extract structured corrections.

    Args:
        design_screenshots: node_id -> PNG bytes from Figma.
        rendered_screenshots: node_id -> PNG bytes from rendered HTML.
        html: The full rendered HTML (for context, not directly used yet).
        sections: Email sections from layout analysis.
        iteration: Current correction loop iteration number.
        global_design_image: Full-frame PNG; passed to the VLM as additional
            context when per-section fidelity falls below
            ``vlm_low_confidence_threshold`` (Phase 50.1).

    Returns:
        VerificationResult with per-section scores and corrections.
    """
    settings = get_settings()
    if not settings.design_sync.vlm_verify_enabled:
        return VerificationResult(
            iteration=iteration,
            fidelity_score=0.0,
            section_scores={},
            corrections=[],
            pixel_diff_pct=0.0,
            converged=False,
        )

    section_scores: dict[str, float] = {}
    all_corrections: list[SectionCorrection] = []
    skip_threshold = settings.design_sync.vlm_verify_diff_skip_threshold
    max_sections = settings.design_sync.vlm_verify_max_sections

    # Build section lookup
    section_map: dict[str, tuple[int, EmailSection]] = {
        s.node_id: (i, s) for i, s in enumerate(sections)
    }

    processed = 0
    for node_id in design_screenshots:
        if node_id not in rendered_screenshots:
            continue
        if processed >= max_sections:
            break

        figma_bytes = design_screenshots[node_id]
        html_bytes = rendered_screenshots[node_id]
        processed += 1

        # 1. ODiff pre-filter
        diff_pct = await _run_odiff_for_section(figma_bytes, html_bytes)
        section_scores[node_id] = diff_pct

        if diff_pct < skip_threshold:
            continue  # Good enough, skip VLM

        # 2. Check cache
        key = _cache_key(figma_bytes, html_bytes)
        if key in _vlm_cache:
            all_corrections.extend(_vlm_cache[key])
            continue

        # 3. VLM analysis — pass full-design PNG when section fidelity falls
        # below the low-confidence threshold (Phase 50.1, Gap 9).
        idx, section = section_map.get(node_id, (0, None))
        section_fidelity = 1.0 - diff_pct / 100.0
        global_for_vlm = (
            global_design_image
            if global_design_image is not None
            and section_fidelity < settings.design_sync.vlm_low_confidence_threshold
            else None
        )
        corrections = await _call_vlm_for_section(
            node_id, idx, figma_bytes, html_bytes, section, global_image=global_for_vlm
        )
        all_corrections.extend(corrections)

        # 4. Cache
        if len(_vlm_cache) >= _CACHE_MAX_SIZE:
            _vlm_cache.clear()
        _vlm_cache[key] = corrections

    avg_diff = sum(section_scores.values()) / max(len(section_scores), 1)
    return VerificationResult(
        iteration=iteration,
        fidelity_score=1.0 - avg_diff / 100.0,
        section_scores=section_scores,
        corrections=all_corrections,
        pixel_diff_pct=avg_diff,
        converged=len(all_corrections) == 0,
    )


async def run_verification_loop(
    html: str,
    design_screenshots: dict[str, bytes],
    sections: list[EmailSection],
    *,
    max_iterations: int | None = None,
    render_client: str = "gmail_web",
    viewport_width: int = 680,
    global_design_image: bytes | None = None,
) -> VerificationLoopResult:
    """Iterative render-compare-correct loop for visual fidelity convergence.

    Each iteration: render HTML -> crop sections -> compare with design ->
    apply corrections. Stops when fidelity target is met, no corrections
    remain, max iterations reached, or a regression is detected.

    Args:
        html: Initial HTML to verify and correct.
        design_screenshots: node_id -> PNG bytes from Figma design.
        sections: Email sections from layout analysis.
        max_iterations: Override config max iterations (for testing).
        render_client: Email client profile for rendering.
        viewport_width: Viewport width for screenshot cropping.
        global_design_image: Full-frame PNG threaded into ``compare_sections``
            for low-fidelity VLM context (Phase 50.1).

    Returns:
        VerificationLoopResult with iteration history and final HTML.
    """
    settings = get_settings()
    ds = settings.design_sync

    if not ds.vlm_verify_enabled:
        return VerificationLoopResult(
            iterations=[],
            final_html=html,
            initial_fidelity=0.0,
            final_fidelity=0.0,
            total_corrections_applied=0,
            total_vlm_cost_tokens=0,
            converged=False,
            reverted=False,
        )

    if max_iterations is None:
        max_iterations = ds.vlm_verify_max_iterations
    target_fidelity = ds.vlm_verify_target_fidelity
    confidence_threshold = ds.vlm_verify_confidence_threshold

    # Late imports to avoid circular dependencies
    from app.design_sync.correction_applicator import apply_corrections
    from app.rendering.local.service import LocalRenderingProvider
    from app.rendering.screenshot_crop import crop_section

    provider = LocalRenderingProvider()
    iterations: list[VerificationResult] = []
    total_corrections = 0
    current_html = html
    prev_html = html
    prev_fidelity = 0.0
    reverted = False

    logger.info(
        "design_sync.verify_loop.starting",
        max_iterations=max_iterations,
        section_count=len(sections),
    )

    for i in range(max_iterations):
        # 1. Render current HTML
        try:
            render_results = await provider.render_screenshots(
                current_html, clients=[render_client]
            )
        except Exception:
            logger.warning(
                "design_sync.verify_loop.render_failed",
                iteration=i,
                exc_info=True,
            )
            break

        if not render_results:
            logger.warning("design_sync.verify_loop.no_render_result", iteration=i)
            break

        image_bytes: bytes = render_results[0].get("image_bytes", b"")

        # 2. Crop per-section screenshots
        rendered_screenshots: dict[str, bytes] = {}
        for s in sections:
            if s.node_id not in design_screenshots:
                continue
            try:
                cropped = crop_section(
                    image_bytes,
                    int(s.y_position if s.y_position is not None else 0),
                    int(s.height if s.height is not None else 200),
                    viewport_width,
                )
                rendered_screenshots[s.node_id] = cropped
            except Exception:
                logger.warning(
                    "design_sync.verify_loop.crop_failed",
                    node_id=s.node_id,
                    iteration=i,
                    exc_info=True,
                )

        # 3. Compare with design
        try:
            result = await compare_sections(
                design_screenshots,
                rendered_screenshots,
                current_html,
                sections,
                iteration=i,
                global_design_image=global_design_image,
            )
        except Exception:
            logger.warning(
                "design_sync.verify_loop.compare_failed",
                iteration=i,
                exc_info=True,
            )
            break

        iterations.append(result)
        logger.info(
            "design_sync.verify_loop.iteration_complete",
            iteration=i,
            fidelity=result.fidelity_score,
            corrections_count=len(result.corrections),
        )

        # 4. Convergence check
        if result.converged or result.fidelity_score >= target_fidelity:
            logger.info(
                "design_sync.verify_loop.converged",
                iteration=i,
                fidelity=result.fidelity_score,
            )
            break

        # 5. Regression check (skip on first iteration)
        if i > 0 and result.fidelity_score < prev_fidelity:
            logger.warning(
                "design_sync.verify_loop.regression_detected",
                iteration=i,
                prev_fidelity=prev_fidelity,
                curr_fidelity=result.fidelity_score,
            )
            # Revert to previous HTML
            current_html = prev_html
            reverted = True
            break

        # 6. Apply corrections
        prev_html = current_html
        prev_fidelity = result.fidelity_score
        try:
            correction_result = apply_corrections(
                current_html,
                result.corrections,
                confidence_threshold=confidence_threshold,
            )
        except Exception:
            logger.warning(
                "design_sync.verify_loop.apply_failed",
                iteration=i,
                exc_info=True,
            )
            break

        current_html = correction_result.html
        total_corrections += len(correction_result.applied)

    initial_fidelity = iterations[0].fidelity_score if iterations else 0.0
    final_fidelity = iterations[-1].fidelity_score if iterations else 0.0

    logger.info(
        "design_sync.verify_loop.completed",
        iterations=len(iterations),
        initial_fidelity=initial_fidelity,
        final_fidelity=final_fidelity,
        total_corrections=total_corrections,
    )

    return VerificationLoopResult(
        iterations=iterations,
        final_html=current_html,
        initial_fidelity=initial_fidelity,
        final_fidelity=final_fidelity,
        total_corrections_applied=total_corrections,
        total_vlm_cost_tokens=0,
        converged=any(r.converged or r.fidelity_score >= target_fidelity for r in iterations),
        reverted=reverted,
    )


async def _run_odiff_for_section(figma_bytes: bytes, html_bytes: bytes) -> float:
    """Run ODiff on two in-memory PNGs, return diff_percentage."""
    from app.rendering.visual_diff import run_odiff

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "design.png"
        curr = Path(tmp) / "rendered.png"
        diff = Path(tmp) / "diff.png"
        base.write_bytes(figma_bytes)
        curr.write_bytes(html_bytes)
        try:
            result = await run_odiff(base, curr, diff, threshold=0.01)
            return result.diff_percentage
        except Exception:
            logger.warning("design_sync.visual_verify.odiff_error", exc_info=True)
            return 100.0  # Treat error as max diff -> don't skip VLM


def _build_vlm_prompt(
    section_idx: int,
    figma_bytes: bytes,
    html_bytes: bytes,
    section: EmailSection | None,
    global_image: bytes | None = None,
) -> list[ContentBlock]:
    """Build multimodal content blocks for VLM comparison.

    When ``global_image`` is provided, a third ImageBlock is appended so the
    VLM can reason about the section's role within the overall email layout
    (Phase 50.1 low-confidence fallback, Gap 9).
    """
    from app.ai.multimodal import ImageBlock, TextBlock

    section_desc = ""
    if section:
        section_desc = f"\nSection type: {section.section_type.value}, index: {section_idx}"

    if global_image is not None:
        prompt_text = (
            "Compare these email section screenshots. "
            "First image: original Figma design (this section). "
            "Second image: rendered HTML (this section). "
            "Third image: full-page Figma design — use it only as context "
            "for what role this section plays in the overall email.\n"
            "For each visible difference between images one and two, return a JSON "
            "array of objects with:\n"
            '- "correction_type": one of "color","font","spacing","layout","content","image"\n'
            '- "css_selector": CSS selector for the element\n'
            '- "css_property": the CSS property to change\n'
            '- "current_value": what the rendered version has\n'
            '- "correct_value": what the design shows\n'
            '- "confidence": 0.0-1.0\n'
            '- "reasoning": brief explanation\n'
            "Only report differences you are confident about. "
            "Return [] if sections look identical."
            f"{section_desc}"
        )
    else:
        prompt_text = (
            "Compare these two email section screenshots. "
            "First image: original Figma design. Second image: rendered HTML.\n"
            "For each visible difference, return a JSON array of objects with:\n"
            '- "correction_type": one of "color","font","spacing","layout","content","image"\n'
            '- "css_selector": CSS selector for the element\n'
            '- "css_property": the CSS property to change\n'
            '- "current_value": what the rendered version has\n'
            '- "correct_value": what the design shows\n'
            '- "confidence": 0.0-1.0\n'
            '- "reasoning": brief explanation\n'
            "Only report differences you are confident about. "
            "Return [] if sections look identical."
            f"{section_desc}"
        )

    blocks: list[ContentBlock] = [
        TextBlock(text=prompt_text),
        ImageBlock(data=figma_bytes, media_type="image/png", source="base64"),
        ImageBlock(data=html_bytes, media_type="image/png", source="base64"),
    ]
    if global_image is not None:
        blocks.append(ImageBlock(data=global_image, media_type="image/png", source="base64"))
    return blocks


async def _call_vlm_for_section(
    node_id: str,
    section_idx: int,
    figma_bytes: bytes,
    html_bytes: bytes,
    section: EmailSection | None,
    *,
    global_image: bytes | None = None,
) -> list[SectionCorrection]:
    """Call VLM for a single section and return parsed corrections."""
    settings = get_settings()
    try:
        from app.ai.capability_registry import ModelCapability
        from app.ai.protocols import Message
        from app.ai.registry import get_registry
        from app.ai.routing import resolve_model, resolve_model_by_capabilities

        model_name = settings.design_sync.vlm_verify_model
        if not model_name:
            model_name = resolve_model_by_capabilities(
                requirements={ModelCapability.VISION},
                tier="standard",
            ) or resolve_model("standard")

        content: list[ContentBlock] = _build_vlm_prompt(
            section_idx, figma_bytes, html_bytes, section, global_image=global_image
        )
        registry = get_registry()
        provider = registry.get_llm(model_name)

        response = await asyncio.wait_for(
            provider.complete(
                messages=[Message(role="user", content=content)],
                model=model_name,
                temperature=0.0,
                max_tokens=2048,
            ),
            timeout=settings.design_sync.vlm_verify_timeout,
        )
        return _parse_vlm_response(response.content, node_id, section_idx)
    except TimeoutError:
        logger.warning("design_sync.visual_verify.vlm_timeout", node_id=node_id)
        return []
    except Exception:
        logger.warning("design_sync.visual_verify.vlm_error", node_id=node_id, exc_info=True)
        return []


def _parse_vlm_response(
    content: str,
    node_id: str,
    section_idx: int,
) -> list[SectionCorrection]:
    """Parse VLM JSON response into SectionCorrection list."""
    try:
        text = content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed = json.loads(text)
        if not isinstance(parsed, list):
            return []
        items = cast(list[Any], parsed)  # type: ignore[redundant-cast]
    except (json.JSONDecodeError, IndexError):
        logger.warning("design_sync.visual_verify.parse_error", node_id=node_id)
        return []

    corrections: list[SectionCorrection] = []
    valid_types = {"color", "font", "spacing", "layout", "content", "image"}
    for raw in items:
        if not isinstance(raw, dict):
            continue
        item = cast(dict[str, Any], raw)
        ctype: str = str(item.get("correction_type", ""))
        if ctype not in valid_types:
            continue
        corrections.append(
            SectionCorrection(
                node_id=node_id,
                section_idx=section_idx,
                correction_type=ctype,  # type: ignore[arg-type]  # validated above
                css_selector=str(item.get("css_selector", "")),
                css_property=str(item.get("css_property", "")),
                current_value=str(item.get("current_value", "")),
                correct_value=str(item.get("correct_value", "")),
                confidence=float(item.get("confidence", 0.5)),
                reasoning=str(item.get("reasoning", "")),
            )
        )
    return corrections
