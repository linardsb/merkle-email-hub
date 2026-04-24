"""VLM-assisted section type classification fallback.

When heuristic component matching falls below the confidence threshold,
uses a vision-language model to classify the section from its screenshot.

Phase 41.5: ``vlm_classify_section()`` — per-section component matcher fallback.
Phase 41.7: ``VLMSectionClassifier`` — batch section *type* classification for
``analyze_layout()`` hybrid merge.

Follows the same patterns as ``ai_content_detector.py`` and
``ai_layout_classifier.py``: bounded LRU cache, graceful error handling,
structured logging.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from typing import Any, cast

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Cache: screenshot hash -> (component_type, confidence)
# Bounded to prevent unbounded memory growth.
_CACHE_MAX_SIZE = 512
_vlm_cache: dict[str, tuple[str, float]] = {}


@dataclass(frozen=True)
class VLMClassificationResult:
    """Result of VLM section classification."""

    component_type: str
    confidence: float
    source: str = "vlm_fallback"


def _screenshot_hash(screenshot: bytes) -> str:
    """Hash screenshot bytes for cache keying."""
    return hashlib.sha256(screenshot).hexdigest()[:16]


def clear_vlm_cache() -> None:
    """Clear the VLM classification cache."""
    _vlm_cache.clear()


async def vlm_classify_section(
    screenshot: bytes,
    candidate_types: list[str],
) -> VLMClassificationResult | None:
    """Classify a section screenshot using a vision-language model.

    Args:
        screenshot: PNG bytes of the section screenshot.
        candidate_types: Component type slugs from the manifest.

    Returns:
        VLMClassificationResult if VLM returns confidence >= 0.5, else None.
    """
    settings = get_settings()
    if not settings.design_sync.vlm_fallback_enabled:
        return None

    # Cache check
    h = _screenshot_hash(screenshot)
    if h in _vlm_cache:
        slug, conf = _vlm_cache[h]
        logger.debug("vlm_classify.cache_hit", hash=h, component_type=slug)
        return VLMClassificationResult(component_type=slug, confidence=conf)

    from app.ai.capability_registry import ModelCapability
    from app.ai.multimodal import ContentBlock, ImageBlock, TextBlock
    from app.ai.protocols import CompletionResponse, Message
    from app.ai.registry import get_registry
    from app.ai.routing import resolve_model, resolve_model_by_capabilities

    # Resolve vision-capable model
    model = resolve_model_by_capabilities(
        requirements={ModelCapability.VISION},
        tier="standard",
    ) or resolve_model("standard")

    registry = get_registry()
    provider = registry.get_llm(model)

    types_list = ", ".join(candidate_types)
    prompt_text = (
        "You are an email design classifier. Given a screenshot of one section "
        "from an email design, classify it into one of these component types:\n\n"
        f"{types_list}\n\n"
        "Respond with JSON only: "
        '{"component_type": "<type>", "confidence": <0.0-1.0>}\n\n'
        "Rules:\n"
        "- Choose the single best matching component type from the list\n"
        "- confidence reflects how clearly the section matches that type\n"
        "- If none match well, use the closest with low confidence"
    )

    content_blocks: list[ContentBlock] = [
        ImageBlock(data=screenshot, media_type="image/png", source="base64"),
        TextBlock(text=prompt_text),
    ]

    messages = [Message(role="user", content=content_blocks)]

    try:
        response: CompletionResponse = await provider.complete(
            messages,
            model=model,
            temperature=0.0,
            max_tokens=128,
        )
        parsed = json.loads(response.content)
        component_type = str(parsed["component_type"])
        confidence = float(parsed["confidence"])
    except Exception:
        logger.warning("vlm_classify.failed", hash=h, exc_info=True)
        return None

    if component_type not in candidate_types:
        logger.warning(
            "vlm_classify.invalid_type",
            hash=h,
            returned_type=component_type,
        )
        return None

    if confidence < 0.5:
        logger.debug("vlm_classify.low_confidence", hash=h, confidence=confidence)
        return None

    # Cache result (bounded)
    if len(_vlm_cache) >= _CACHE_MAX_SIZE:
        _vlm_cache.clear()
    _vlm_cache[h] = (component_type, confidence)

    logger.info(
        "vlm_classify.success",
        hash=h,
        component_type=component_type,
        confidence=confidence,
    )
    return VLMClassificationResult(component_type=component_type, confidence=confidence)


# ── Phase 41.7: Batch Section Type Classification ──


@dataclass(frozen=True)
class VLMSectionClassification:
    """Result of VLM section *type* classification for layout analysis."""

    node_id: str
    section_type: str  # EmailSectionType value
    confidence: float
    reasoning: str = ""
    column_layout: str | None = None  # ColumnLayout value or None
    content_signals: tuple[str, ...] = ()


# Cache: combined screenshot hash → dict of classifications
_SECTION_CACHE_MAX_SIZE = 64
_section_cache: dict[str, dict[str, VLMSectionClassification]] = {}


def clear_section_cache() -> None:
    """Clear the section classification cache."""
    _section_cache.clear()


def _get_section_types() -> list[str]:
    """Derive valid section types from EmailSectionType enum (avoids stale list)."""
    from app.design_sync.figma.layout_analyzer import EmailSectionType

    return [t.value for t in EmailSectionType]


class VLMSectionClassifier:
    """Batch VLM section type classifier for ``analyze_layout()`` hybrid merge."""

    async def classify_sections(
        self,
        frame_screenshots: dict[str, bytes],
        frame_metadata: list[dict[str, Any]],
    ) -> dict[str, VLMSectionClassification]:
        """Classify multiple frame screenshots into email section types.

        Args:
            frame_screenshots: ``node_id → PNG bytes`` from
                ``FigmaDesignSyncService.export_frame_screenshots()``.
            frame_metadata: Per-frame metadata dicts with keys
                ``node_id``, ``name``, ``index``, ``total``.

        Returns:
            ``node_id → VLMSectionClassification`` dict.  Empty on
            error/timeout/disabled.
        """
        settings = get_settings()
        if not settings.design_sync.vlm_classification_enabled:
            return {}

        if not frame_screenshots:
            return {}

        # Cache check — incrementally hash screenshots to avoid large temp alloc
        hasher = hashlib.sha256()
        for m in frame_metadata:
            nid = m["node_id"]
            if nid in frame_screenshots:
                hasher.update(frame_screenshots[nid])
        cache_key = hasher.hexdigest()[:16]
        if cache_key in _section_cache:
            logger.debug("design_sync.vlm_classification.cache_hit", key=cache_key)
            return _section_cache[cache_key]

        try:
            result = await asyncio.wait_for(
                self._call_vlm(frame_screenshots, frame_metadata),
                timeout=settings.design_sync.vlm_classification_timeout,
            )
        except TimeoutError:
            logger.warning("design_sync.vlm_classification.timeout")
            return {}
        except Exception:
            logger.warning("design_sync.vlm_classification.error", exc_info=True)
            return {}

        # Cache result (bounded)
        if len(_section_cache) >= _SECTION_CACHE_MAX_SIZE:
            _section_cache.clear()
        _section_cache[cache_key] = result
        return result

    async def _call_vlm(
        self,
        frame_screenshots: dict[str, bytes],
        frame_metadata: list[dict[str, Any]],
    ) -> dict[str, VLMSectionClassification]:
        from app.ai.capability_registry import ModelCapability
        from app.ai.multimodal import ContentBlock, ImageBlock, TextBlock
        from app.ai.protocols import CompletionResponse, Message
        from app.ai.registry import get_registry
        from app.ai.routing import resolve_model, resolve_model_by_capabilities

        settings = get_settings()

        # Resolve model — prefer config override, then vision-capable
        model_id = settings.design_sync.vlm_classification_model
        if not model_id:
            model_id = resolve_model_by_capabilities(
                requirements={ModelCapability.VISION},
                tier="standard",
            ) or resolve_model("standard")

        registry = get_registry()
        provider = registry.get_llm(model_id)

        # Build multimodal message: system prompt + images + metadata
        section_types = _get_section_types()
        types_list = ", ".join(section_types)
        system_prompt = (
            "You are an email design section classifier. You will see screenshots "
            "of individual sections from an email design, each labeled with a frame "
            "number and name.\n\n"
            "For each frame, classify it into one of these section types:\n"
            f"{types_list}\n\n"
            "Also detect the column layout: single, two-column, three-column, "
            "or multi-column.\n\n"
            "Respond with a JSON array, one object per frame:\n"
            '[{"node_id": "<id>", "section_type": "<type>", "confidence": <0.0-1.0>, '
            '"reasoning": "<brief>", "column_layout": "<layout>", '
            '"content_signals": ["<signal>", ...]}]\n\n'
            "Rules:\n"
            "- Classify based on visual appearance, not frame names\n"
            "- hero: large image or prominent visual with heading\n"
            "- header: logo, brand name, compact top bar\n"
            "- footer: small text, legal, unsubscribe links\n"
            "- cta: prominent button or call-to-action\n"
            "- social: social media icons\n"
            "- content: body text, product grids, articles\n"
            "- nav: horizontal navigation links\n"
            "- divider/spacer: thin lines or empty gaps\n"
            "- preheader: very small text at very top\n"
        )

        content_blocks: list[ContentBlock] = [TextBlock(text=system_prompt)]

        for meta in frame_metadata:
            nid = meta["node_id"]
            if nid not in frame_screenshots:
                continue
            content_blocks.append(
                ImageBlock(
                    data=frame_screenshots[nid],
                    media_type="image/png",
                    source="base64",
                )
            )
            content_blocks.append(
                TextBlock(
                    text=(
                        f"Frame {meta.get('index', '?')}/{meta.get('total', '?')}: "
                        f"node_id={nid}, name={meta.get('name', 'unnamed')}"
                    )
                )
            )

        messages = [Message(role="user", content=content_blocks)]

        response: CompletionResponse = await provider.complete(
            messages,
            model=model_id,
            temperature=0.0,
            max_tokens=1024,
        )

        return self._parse_response(response.content, frame_screenshots)

    def _parse_response(
        self,
        content: str,
        frame_screenshots: dict[str, bytes],
    ) -> dict[str, VLMSectionClassification]:
        """Parse VLM JSON array response into classification dict."""
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("design_sync.vlm_classification.parse_error")
            return {}

        if not isinstance(parsed, list):
            logger.warning("design_sync.vlm_classification.not_array")
            return {}

        results: dict[str, VLMSectionClassification] = {}
        parsed_list: list[dict[str, Any]] = [
            cast(dict[str, Any], x)
            for x in cast(list[Any], parsed)  # type: ignore[redundant-cast]
            if isinstance(x, dict)
        ]
        for item in parsed_list:
            nid = str(item.get("node_id", ""))
            section_type = str(item.get("section_type", "unknown"))
            if nid not in frame_screenshots:
                continue
            if section_type not in _get_section_types():
                section_type = "unknown"

            confidence = float(item.get("confidence", 0.0))
            col_layout: str | None = item.get("column_layout")
            if col_layout is not None:
                col_layout = str(col_layout)
            raw_signals: list[Any] = list(item.get("content_signals", []))
            results[nid] = VLMSectionClassification(
                node_id=nid,
                section_type=section_type,
                confidence=confidence,
                reasoning=str(item.get("reasoning", "")),
                column_layout=col_layout,
                content_signals=tuple(str(s) for s in raw_signals),
            )

        logger.info(
            "design_sync.vlm_classification.success",
            count=len(results),
        )
        return results
