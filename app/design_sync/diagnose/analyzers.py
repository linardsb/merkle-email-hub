# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
"""Per-stage diagnostic analyzers for the conversion pipeline."""

from __future__ import annotations

import re
import time
from typing import Any

from app.design_sync.component_matcher import ComponentMatch
from app.design_sync.component_renderer import RenderedSection
from app.design_sync.diagnose.models import (
    DataLossEvent,
    DesignSummary,
    SectionTrace,
    StageResult,
)
from app.design_sync.figma.layout_analyzer import (
    _SECTION_PATTERNS,
    DesignLayoutDescription,
    EmailSection,
    EmailSectionType,
)
from app.design_sync.protocol import DesignFileStructure, DesignNode, DesignNodeType

_HTML_PREVIEW_LIMIT = 3000
_SLOT_PATTERN = re.compile(r'data-slot="([^"]+)"')


def analyze_design_tree(
    structure: DesignFileStructure,
    raw_figma_json: dict[str, Any] | None = None,
) -> tuple[DesignSummary, list[DataLossEvent]]:
    """Analyze the design tree for patterns and data loss."""
    type_counts: dict[str, int] = {}
    max_depth = 0
    auto_layout_count = 0
    total_nodes = 0
    data_loss: list[DataLossEvent] = []
    image_fill_frames: list[dict[str, str]] = []

    # Build pattern lookup (lowercase keywords)
    all_patterns: list[str] = []
    for keywords in _SECTION_PATTERNS.values():
        all_patterns.extend(keywords)

    naming_hits = 0
    naming_total = 0
    naming_misses: list[str] = []

    def _walk(node: DesignNode, depth: int) -> None:
        nonlocal max_depth, auto_layout_count, total_nodes, naming_hits, naming_total
        total_nodes += 1
        max_depth = max(max_depth, depth)

        type_name = node.type.value
        type_counts[type_name] = type_counts.get(type_name, 0) + 1

        if node.layout_mode is not None:
            auto_layout_count += 1

        # Check naming compliance for top-level FRAME/COMPONENT candidates
        # depth 1 = direct children of PAGE nodes (the email sections)
        if depth == 1 and node.type in (DesignNodeType.FRAME, DesignNodeType.COMPONENT):
            naming_total += 1
            name_lower = node.name.lower()
            matched = any(kw in name_lower for kw in all_patterns)
            if matched:
                naming_hits += 1
            else:
                naming_misses.append(node.name)

        # Detect whitespace-only TEXT nodes (data loss #3)
        if (
            node.type == DesignNodeType.TEXT
            and node.text_content is not None
            and node.text_content.strip() == ""
        ):
            data_loss.append(
                DataLossEvent(
                    type="text_whitespace_only",
                    node_id=node.id,
                    node_name=node.name,
                    detail=f"TEXT node has whitespace-only content: {node.text_content!r}",
                    stage="design_tree",
                )
            )

        for child in node.children:
            _walk(child, depth + 1)

    for page in structure.pages:
        _walk(page, 0)

    # Detect IMAGE fills on FRAMEs from raw JSON (data loss #2)
    if raw_figma_json:
        _detect_image_fills(raw_figma_json, image_fill_frames, data_loss)

    naming_compliance = (naming_hits / naming_total * 100.0) if naming_total > 0 else 100.0

    summary = DesignSummary(
        total_nodes=total_nodes,
        node_type_counts=type_counts,
        max_tree_depth=max_depth,
        image_fill_frames=tuple(image_fill_frames),
        auto_layout_frames=auto_layout_count,
        naming_compliance=round(naming_compliance, 1),
        naming_misses=tuple(naming_misses),
    )
    return summary, data_loss


def _detect_image_fills(
    raw_json: dict[str, Any],
    image_fill_frames: list[dict[str, str]],
    data_loss: list[DataLossEvent],
) -> None:
    """Walk raw Figma JSON to find FRAME nodes with IMAGE fills."""

    def _walk_raw(node: dict[str, Any]) -> None:
        node_type = node.get("type", "")
        fills = node.get("fills", [])
        if isinstance(fills, list) and node_type in ("FRAME", "GROUP", "COMPONENT", "INSTANCE"):
            for fill in fills:
                if isinstance(fill, dict) and fill.get("type") == "IMAGE":
                    node_id = str(node.get("id", ""))
                    node_name = str(node.get("name", ""))
                    image_fill_frames.append({"node_id": node_id, "name": node_name})
                    data_loss.append(
                        DataLossEvent(
                            type="image_fill_on_frame",
                            node_id=node_id,
                            node_name=node_name,
                            detail=(
                                f"FRAME '{node_name}' has an IMAGE fill "
                                "which the parser silently ignores"
                            ),
                            stage="design_tree",
                        )
                    )
                    break
        for child in node.get("children", []):
            if isinstance(child, dict):
                _walk_raw(child)

    # Raw JSON may be the full Figma document or a sub-tree
    document = raw_json.get("document", raw_json)
    if isinstance(document, dict):
        for child in document.get("children", []):
            if isinstance(child, dict):
                _walk_raw(child)


def analyze_layout_stage(
    structure: DesignFileStructure,
    layout: DesignLayoutDescription,
) -> StageResult:
    """Analyze layout analysis stage for data loss and quality."""
    t0 = time.perf_counter()
    data_loss: list[DataLossEvent] = []
    warnings: list[str] = []

    # Count TEXT/IMAGE nodes in input tree
    input_text_count = 0
    input_image_count = 0

    def _count_nodes(node: DesignNode) -> None:
        nonlocal input_text_count, input_image_count
        if node.type == DesignNodeType.TEXT:
            input_text_count += 1
        elif node.type == DesignNodeType.IMAGE:
            input_image_count += 1
        for child in node.children:
            _count_nodes(child)

    for page in structure.pages:
        _count_nodes(page)

    # Compare with layout output
    text_delta = input_text_count - layout.total_text_blocks
    if text_delta > 0:
        warnings.append(f"{text_delta} TEXT node(s) in design tree not captured in layout analysis")

    image_delta = input_image_count - layout.total_images
    if image_delta > 0:
        warnings.append(
            f"{image_delta} IMAGE node(s) in design tree not captured in layout analysis"
        )

    # Flag UNKNOWN sections
    for section in layout.sections:
        if section.section_type == EmailSectionType.UNKNOWN:
            data_loss.append(
                DataLossEvent(
                    type="unknown_section_type",
                    node_id=section.node_id,
                    node_name=section.node_name,
                    detail=(
                        f"Section '{section.node_name}' classified as UNKNOWN — "
                        "will get generic component match"
                    ),
                    stage="layout_analysis",
                )
            )

    # Detect nested images missed (data loss #8)
    for section in layout.sections:
        if not section.images:
            nested_images = _count_nested_images(structure, section.node_id)
            if nested_images > 0:
                data_loss.append(
                    DataLossEvent(
                        type="nested_images_missed",
                        node_id=section.node_id,
                        node_name=section.node_name,
                        detail=(
                            f"Section has {nested_images} nested IMAGE node(s) "
                            "not detected by layout analyzer"
                        ),
                        stage="layout_analysis",
                    )
                )

    elapsed = (time.perf_counter() - t0) * 1000.0
    return StageResult(
        name="layout_analysis",
        elapsed_ms=round(elapsed, 2),
        input_summary={
            "text_nodes": input_text_count,
            "image_nodes": input_image_count,
            "pages": len(structure.pages),
        },
        output_summary={
            "sections": len(layout.sections),
            "total_text_blocks": layout.total_text_blocks,
            "total_images": layout.total_images,
            "overall_width": layout.overall_width,
        },
        data_loss=tuple(data_loss),
        warnings=tuple(warnings),
    )


def _count_nested_images(structure: DesignFileStructure, node_id: str) -> int:
    """Count IMAGE descendants of a specific node in the design tree."""
    target = _find_node(structure, node_id)
    if target is None:
        return 0
    count = 0

    def _walk(node: DesignNode) -> None:
        nonlocal count
        if node.type == DesignNodeType.IMAGE:
            count += 1
        for child in node.children:
            _walk(child)

    for child in target.children:
        _walk(child)
    return count


def _find_node(structure: DesignFileStructure, node_id: str) -> DesignNode | None:
    """Find a node by ID in the design tree."""

    def _search(node: DesignNode) -> DesignNode | None:
        if node.id == node_id:
            return node
        for child in node.children:
            found = _search(child)
            if found:
                return found
        return None

    for page in structure.pages:
        found = _search(page)
        if found:
            return found
    return None


def analyze_matching_stage(
    sections: list[EmailSection],
    matches: list[ComponentMatch],
) -> StageResult:
    """Analyze component matching stage for data loss and quality."""
    t0 = time.perf_counter()
    data_loss: list[DataLossEvent] = []
    warnings: list[str] = []

    for section, match in zip(sections, matches, strict=False):
        # Flag low confidence matches
        if match.confidence < 0.8:
            warnings.append(
                f"Section '{section.node_name}' matched to '{match.component_slug}' "
                f"with low confidence ({match.confidence:.1f})"
            )

        # Detect text count reduction (data loss #10)
        text_fills = [f for f in match.slot_fills if f.slot_type == "text"]
        if len(section.texts) > 1 and len(text_fills) <= 1:
            data_loss.append(
                DataLossEvent(
                    type="text_count_reduction",
                    node_id=section.node_id,
                    node_name=section.node_name,
                    detail=(
                        f"Section has {len(section.texts)} text blocks "
                        f"but only {len(text_fills)} text slot fill(s) — "
                        "content may be joined or lost"
                    ),
                    stage="component_matching",
                )
            )

        # Flag empty slot fills for sections with content (data loss #9)
        if not match.slot_fills and (section.texts or section.images or section.buttons):
            data_loss.append(
                DataLossEvent(
                    type="empty_slot_fills",
                    node_id=section.node_id,
                    node_name=section.node_name,
                    detail=(
                        f"Component '{match.component_slug}' has no slot fills "
                        f"despite section having content "
                        f"(texts={len(section.texts)}, images={len(section.images)}, "
                        f"buttons={len(section.buttons)})"
                    ),
                    stage="component_matching",
                )
            )

    elapsed = (time.perf_counter() - t0) * 1000.0
    return StageResult(
        name="component_matching",
        elapsed_ms=round(elapsed, 2),
        input_summary={"sections": len(sections)},
        output_summary={
            "matches": len(matches),
            "slugs": [m.component_slug for m in matches],
            "avg_confidence": (
                round(sum(m.confidence for m in matches) / len(matches), 2) if matches else 0.0
            ),
        },
        data_loss=tuple(data_loss),
        warnings=tuple(warnings),
    )


def analyze_rendering_stage(
    matches: list[ComponentMatch],
    rendered: list[RenderedSection],
) -> StageResult:
    """Analyze rendering stage for fallbacks and unfilled slots."""
    t0 = time.perf_counter()
    data_loss: list[DataLossEvent] = []
    warnings: list[str] = []

    for match, section in zip(matches, rendered, strict=False):
        # Detect fallback rendering (data loss #11)
        if section.component_slug != match.component_slug:
            data_loss.append(
                DataLossEvent(
                    type="fallback_rendering",
                    node_id=match.section.node_id,
                    node_name=match.section.node_name,
                    detail=(
                        f"Expected component '{match.component_slug}' "
                        f"but rendered as '{section.component_slug}' (fallback)"
                    ),
                    stage="rendering",
                )
            )

        # Count unfilled data-slot attributes in rendered HTML
        slot_pattern = _SLOT_PATTERN
        all_slots = set(slot_pattern.findall(section.html))
        filled_slot_ids = {f.slot_id for f in match.slot_fills}
        unfilled = all_slots - filled_slot_ids
        if unfilled:
            warnings.append(
                f"Component '{section.component_slug}' has unfilled slots: "
                f"{', '.join(sorted(unfilled))}"
            )

    elapsed = (time.perf_counter() - t0) * 1000.0
    return StageResult(
        name="rendering",
        elapsed_ms=round(elapsed, 2),
        input_summary={"matches": len(matches)},
        output_summary={
            "rendered_sections": len(rendered),
            "total_html_chars": sum(len(s.html) for s in rendered),
        },
        data_loss=tuple(data_loss),
        warnings=tuple(warnings),
    )


def analyze_assembly_stage(
    rendered: list[RenderedSection],
    final_html: str,
) -> StageResult:
    """Analyze HTML assembly for tag balance and structural issues."""
    t0 = time.perf_counter()
    data_loss: list[DataLossEvent] = []
    warnings: list[str] = []

    # Check <table> tag balance
    table_opens = len(re.findall(r"<table\b", final_html, re.IGNORECASE))
    table_closes = len(re.findall(r"</table>", final_html, re.IGNORECASE))
    if table_opens != table_closes:
        warnings.append(f"Unbalanced <table> tags: {table_opens} opens vs {table_closes} closes")

    # Check MSO conditional balance
    mso_opens = len(re.findall(r"<!--\[if\s+mso\]>", final_html))
    mso_closes = len(re.findall(r"<!\[endif\]-->", final_html))
    if mso_opens != mso_closes:
        warnings.append(f"Unbalanced MSO conditionals: {mso_opens} opens vs {mso_closes} closes")

    # Check CSS brace balance in <style> blocks
    style_blocks = re.findall(r"<style[^>]*>(.*?)</style>", final_html, re.DOTALL)
    for i, block in enumerate(style_blocks):
        open_braces = block.count("{")
        close_braces = block.count("}")
        if open_braces != close_braces:
            warnings.append(
                f"CSS brace imbalance in <style> block {i}: "
                f"{open_braces} opens vs {close_braces} closes"
            )

    elapsed = (time.perf_counter() - t0) * 1000.0
    return StageResult(
        name="assembly",
        elapsed_ms=round(elapsed, 2),
        input_summary={
            "rendered_sections": len(rendered),
            "total_section_html_chars": sum(len(s.html) for s in rendered),
        },
        output_summary={
            "final_html_length": len(final_html),
            "table_count": table_opens,
            "style_blocks": len(style_blocks),
        },
        data_loss=tuple(data_loss),
        warnings=tuple(warnings),
    )


def analyze_post_processing(
    before_html: str,
    after_html: str,
) -> StageResult:
    """Analyze post-processing (sanitization) for changes and remaining issues."""
    t0 = time.perf_counter()
    data_loss: list[DataLossEvent] = []
    warnings: list[str] = []

    # Count remaining empty src attributes (data loss #12)
    empty_src_count = len(re.findall(r'src=""', after_html))
    if empty_src_count > 0:
        warnings.append(f"{empty_src_count} image(s) with empty src attribute remaining")
        data_loss.append(
            DataLossEvent(
                type="unfilled_image_src",
                node_id="",
                node_name="",
                detail=f'{empty_src_count} <img> tag(s) with src="" after post-processing',
                stage="post_processing",
            )
        )

    # Count div→table conversions
    before_divs = len(re.findall(r"<div\b", before_html, re.IGNORECASE))
    after_divs = len(re.findall(r"<div\b", after_html, re.IGNORECASE))
    div_removed = before_divs - after_divs

    length_delta = len(after_html) - len(before_html)

    elapsed = (time.perf_counter() - t0) * 1000.0
    return StageResult(
        name="post_processing",
        elapsed_ms=round(elapsed, 2),
        input_summary={"html_length": len(before_html), "div_count": before_divs},
        output_summary={
            "html_length": len(after_html),
            "div_count": after_divs,
            "divs_removed": div_removed,
            "length_delta": length_delta,
        },
        data_loss=tuple(data_loss),
        warnings=tuple(warnings),
    )


def build_section_traces(
    layout: DesignLayoutDescription,
    matches: list[ComponentMatch],
    rendered: list[RenderedSection],
    *,
    verification_results: dict[int, tuple[float, int]] | None = None,
    generation_methods: dict[int, str] | None = None,
    vlm_classifications: dict[int, tuple[str, float]] | None = None,
) -> list[SectionTrace]:
    """Build per-section diagnostic traces by zipping pipeline stages."""
    traces: list[SectionTrace] = []

    for i, section in enumerate(layout.sections):
        match = matches[i] if i < len(matches) else None
        rendered_section = rendered[i] if i < len(rendered) else None

        # Compute unfilled slots from rendered HTML
        unfilled: list[str] = []
        if rendered_section and match:
            slot_pattern = _SLOT_PATTERN
            all_slots = set(slot_pattern.findall(rendered_section.html))
            filled_ids = {f.slot_id for f in match.slot_fills}
            unfilled = sorted(all_slots - filled_ids)

        # Build slot fill summaries
        slot_summaries: list[dict[str, str]] = []
        if match:
            for fill in match.slot_fills:
                slot_summaries.append(
                    {
                        "slot_id": fill.slot_id,
                        "slot_type": fill.slot_type,
                        "value_preview": fill.value[:80] if fill.value else "",
                    }
                )

        html_preview = ""
        if rendered_section:
            html_preview = rendered_section.html[:_HTML_PREVIEW_LIMIT]

        # Verification / generation / VLM metadata for this section
        v_fidelity: float | None = None
        v_corrections = 0
        if verification_results and i in verification_results:
            v_fidelity, v_corrections = verification_results[i]

        gen_method = "template"
        if generation_methods and i in generation_methods:
            gen_method = generation_methods[i]

        vlm_type = ""
        vlm_conf = 0.0
        if vlm_classifications and i in vlm_classifications:
            vlm_type, vlm_conf = vlm_classifications[i]

        traces.append(
            SectionTrace(
                section_idx=i,
                node_id=section.node_id,
                node_name=section.node_name,
                classified_type=section.section_type.value,
                matched_component=match.component_slug if match else "",
                match_confidence=match.confidence if match else 0.0,
                texts_found=len(section.texts),
                images_found=len(section.images),
                buttons_found=len(section.buttons),
                slot_fills=tuple(slot_summaries),
                unfilled_slots=tuple(unfilled),
                html_preview=html_preview,
                vlm_classification=vlm_type,
                vlm_confidence=vlm_conf,
                verification_fidelity=v_fidelity,
                corrections_applied=v_corrections,
                generation_method=gen_method,
            )
        )

    return traces
