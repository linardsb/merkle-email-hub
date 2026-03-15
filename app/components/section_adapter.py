"""Bridge between component library and template composition pipeline.

Converts QA-validated ComponentVersion records into SectionBlock instances
usable by TemplateComposer and the agent pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from cssselect import SelectorSyntaxError
from lxml import html as lxml_html
from lxml.etree import LxmlError

from app.ai.templates.composer import SectionBlock
from app.ai.templates.models import SlotType, TemplateSlot
from app.components.sanitize import sanitize_component_html
from app.core.exceptions import DomainValidationError
from app.core.logging import get_logger
from app.qa_engine.repair.pipeline import RepairPipeline

if TYPE_CHECKING:
    from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)

MIN_QA_SCORE = 0.8


@dataclass(frozen=True)
class SlotHint:
    """Describes a content slot within a component."""

    slot_id: str
    slot_type: SlotType
    selector: str
    required: bool = True
    max_chars: int | None = None


class ComponentVersionLike(Protocol):
    """Structural type for objects that look like a ComponentVersion."""

    @property
    def id(self) -> int: ...
    @property
    def component_id(self) -> int: ...
    @property
    def version_number(self) -> int: ...
    @property
    def html_source(self) -> str: ...


class AdaptationError(DomainValidationError):
    """Raised when a component cannot meet quality threshold after repair."""


class SectionAdapter:
    """Converts ComponentVersion -> SectionBlock via repair pipeline + QA validation."""

    def __init__(self, repair_pipeline: RepairPipeline | None = None) -> None:
        self._pipeline = repair_pipeline or RepairPipeline()

    def adapt(
        self,
        version: ComponentVersionLike,
        slot_hints: list[SlotHint],
    ) -> SectionBlock:
        """Convert a component version into a composition-ready SectionBlock.

        Steps:
          1. Sanitize HTML (XSS stripping)
          2. Run repair pipeline (MSO, dark mode, a11y hardening)
          3. Inject data-slot markers via lxml DOM manipulation
          4. Extract metadata (dark mode classes, MSO wrappers)
          5. Build SectionBlock

        Args:
            version: The component version to adapt.
            slot_hints: Content slot annotations for the component.

        Returns:
            SectionBlock ready for TemplateComposer.compose().

        Raises:
            AdaptationError: If HTML cannot be repaired to quality threshold.
        """
        # 1. Sanitize
        html = sanitize_component_html(version.html_source)

        # 2. Repair
        repair_result = self._pipeline.run(html)
        html = repair_result.html

        if repair_result.repairs_applied:
            logger.info(
                "section_adapter.repairs_applied",
                component_id=version.component_id,
                version_id=version.id,
                count=len(repair_result.repairs_applied),
            )

        # 3. Inject data-slot markers
        html = _inject_slot_markers(html, slot_hints)

        # 4. Extract metadata
        has_mso = "<!--[if mso]>" in html
        dark_mode_classes = _extract_dark_mode_classes(html)

        # 5. Build slot definitions as TemplateSlot tuples
        template_slots = tuple(
            TemplateSlot(
                slot_id=hint.slot_id,
                slot_type=hint.slot_type,
                selector=hint.selector,
                required=hint.required,
                max_chars=hint.max_chars,
                placeholder="",
            )
            for hint in slot_hints
        )

        block_id = f"component_{version.component_id}_v{version.version_number}"

        logger.info(
            "section_adapter.adapted",
            block_id=block_id,
            slot_count=len(slot_hints),
            has_mso=has_mso,
            dark_mode_classes=len(dark_mode_classes),
        )

        return SectionBlock(
            block_id=block_id,
            display_name=f"Component #{version.component_id} v{version.version_number}",
            html=html,
            slot_definitions=template_slots,
            has_mso_wrapper=has_mso,
            dark_mode_classes=dark_mode_classes,
        )

    def validate_for_composition(
        self,
        block: SectionBlock,
        qa_results: list[QACheckResult],
    ) -> list[QACheckResult]:
        """Validate a SectionBlock meets quality threshold for composition.

        Args:
            block: The adapted section block.
            qa_results: Pre-computed QA check results for the block's HTML.

        Returns:
            The QA results list (for caller inspection).

        Raises:
            AdaptationError: If average QA score < MIN_QA_SCORE.
        """
        if not qa_results:
            raise AdaptationError(f"No QA results provided for block '{block.block_id}'")

        avg_score = sum(r.score for r in qa_results) / len(qa_results)

        if avg_score < MIN_QA_SCORE:
            failing = [r for r in qa_results if not r.passed]
            details = "; ".join(f"{r.check_name}: {r.score:.2f}" for r in failing[:5])
            raise AdaptationError(
                f"Block '{block.block_id}' QA score {avg_score:.2f} "
                f"< {MIN_QA_SCORE} threshold. Failures: {details}"
            )

        logger.info(
            "section_adapter.validated",
            block_id=block.block_id,
            avg_score=avg_score,
            check_count=len(qa_results),
        )
        return qa_results


# ── Private helpers ──


def _inject_slot_markers(html: str, slot_hints: list[SlotHint]) -> str:
    """Inject data-slot attributes into HTML using lxml DOM manipulation.

    Uses CSS selectors from slot hints to find target elements and add
    data-slot attributes. Falls back gracefully if a selector doesn't match.
    """
    if not slot_hints:
        return html

    try:
        doc = lxml_html.fromstring(html)
    except LxmlError:
        logger.warning("section_adapter.parse_failed", hint_count=len(slot_hints))
        return html

    for hint in slot_hints:
        try:
            elements = doc.cssselect(hint.selector)
            if not elements:
                logger.warning(
                    "section_adapter.selector_no_match",
                    slot_id=hint.slot_id,
                    selector=hint.selector,
                )
                continue
            elements[0].set("data-slot", hint.slot_id)
        except (SelectorSyntaxError, LxmlError):
            logger.warning(
                "section_adapter.slot_injection_failed",
                slot_id=hint.slot_id,
                selector=hint.selector,
            )

    return lxml_html.tostring(doc, encoding="unicode")


def _extract_dark_mode_classes(html: str) -> tuple[str, ...]:
    """Extract dark-* CSS class names from HTML."""
    classes: set[str] = set()
    for match in re.finditer(r'class="([^"]*)"', html):
        for cls in match.group(1).split():
            if cls.startswith("dark-"):
                classes.add(cls)
    return tuple(sorted(classes))


# Cache keyed by (version_id, slot_hints) — version_id is a unique PK and
# versions are immutable, so html_source is not needed in the key.
_adapt_cache: dict[
    tuple[int, tuple[tuple[str, str, str, bool, int | None], ...]], SectionBlock
] = {}
_CACHE_MAX_SIZE = 256


def get_cached_section(
    version: ComponentVersionLike,
    slot_hints: list[SlotHint],
) -> SectionBlock:
    """Get or create a cached SectionBlock for a component version.

    Component versions are immutable once created, so the cache is safe.
    """
    hints_key = tuple(
        (h.slot_id, h.slot_type, h.selector, h.required, h.max_chars) for h in slot_hints
    )
    cache_key = (version.id, hints_key)

    if cache_key in _adapt_cache:
        return _adapt_cache[cache_key]

    adapter = SectionAdapter()
    block = adapter.adapt(version, slot_hints)

    # Evict oldest entries if over capacity
    if len(_adapt_cache) >= _CACHE_MAX_SIZE:
        oldest_key = next(iter(_adapt_cache))
        del _adapt_cache[oldest_key]

    _adapt_cache[cache_key] = block
    return block
