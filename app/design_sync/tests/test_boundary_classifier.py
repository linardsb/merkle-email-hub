"""Tests for section-boundary classifier (Phase 50.2)."""

from __future__ import annotations

import io

import numpy as np
from PIL import Image

from app.design_sync.bgcolor_propagator import (
    SectionBoundary,
    classify_section_boundaries,
)
from app.design_sync.figma.layout_analyzer import (
    EmailSection,
    EmailSectionType,
    analyze_layout,
)
from app.design_sync.protocol import DesignFileStructure, DesignNode, DesignNodeType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_png(rows: list[tuple[tuple[int, int, int], int]], width: int = 600) -> bytes:
    """Build a vertical-stripe PNG from a list of ``(rgb, row_count)`` segments."""
    arr = np.zeros((sum(h for _, h in rows), width, 3), dtype=np.uint8)
    y = 0
    for color, count in rows:
        arr[y : y + count, :, :] = color
        y += count
    img = Image.fromarray(arr, "RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _section(
    *,
    node_id: str,
    y: float,
    height: float,
    section_type: EmailSectionType = EmailSectionType.CONTENT,
) -> EmailSection:
    return EmailSection(
        section_type=section_type,
        node_id=node_id,
        node_name=f"Section-{node_id}",
        y_position=y,
        width=600.0,
        height=height,
    )


# ---------------------------------------------------------------------------
# classify_section_boundaries — pair semantics
# ---------------------------------------------------------------------------


def test_classify_continuous_pair() -> None:
    # 100px solid red on top, 100px solid red on bottom — same color → continuous
    png = _build_png([((255, 0, 0), 200)])
    sections = [
        _section(node_id="a", y=0, height=100),
        _section(node_id="b", y=100, height=100),
    ]
    result = classify_section_boundaries(sections, global_design_image=png)

    assert result["a"].boundary_below == "continuous_with_below"
    assert result["b"].boundary_above == "continuous_with_above"


def test_classify_hard_break() -> None:
    # Red top section, blue bottom section — colors differ greatly → hard_break
    png = _build_png([((255, 0, 0), 100), ((0, 0, 255), 100)])
    sections = [
        _section(node_id="a", y=0, height=100),
        _section(node_id="b", y=100, height=100),
    ]
    result = classify_section_boundaries(sections, global_design_image=png)

    assert result["a"].boundary_below == "hard_break"
    assert result["b"].boundary_above == "hard_break"


def test_classify_within_threshold() -> None:
    # Δ=4 across all channels → still continuous at default threshold=5
    png = _build_png([((100, 100, 100), 100), ((104, 104, 104), 100)])
    sections = [
        _section(node_id="a", y=0, height=100),
        _section(node_id="b", y=100, height=100),
    ]
    result = classify_section_boundaries(sections, global_design_image=png)

    assert result["a"].boundary_below == "continuous_with_below"
    assert result["b"].boundary_above == "continuous_with_above"


def test_classify_above_threshold() -> None:
    # Δ=10 → hard_break with default threshold=5
    png = _build_png([((100, 100, 100), 100), ((110, 110, 110), 100)])
    sections = [
        _section(node_id="a", y=0, height=100),
        _section(node_id="b", y=100, height=100),
    ]
    result = classify_section_boundaries(sections, global_design_image=png)

    assert result["a"].boundary_below == "hard_break"
    assert result["b"].boundary_above == "hard_break"


def test_classify_three_sections_chain() -> None:
    # A→B continuous (red→red), B→C hard_break (red→green)
    png = _build_png([((200, 50, 50), 100), ((200, 50, 50), 100), ((50, 200, 50), 100)])
    sections = [
        _section(node_id="a", y=0, height=100),
        _section(node_id="b", y=100, height=100),
        _section(node_id="c", y=200, height=100),
    ]
    result = classify_section_boundaries(sections, global_design_image=png)

    assert result["a"].boundary_above == "unknown"
    assert result["a"].boundary_below == "continuous_with_below"
    assert result["b"].boundary_above == "continuous_with_above"
    assert result["b"].boundary_below == "hard_break"
    assert result["c"].boundary_above == "hard_break"
    assert result["c"].boundary_below == "unknown"


def test_classify_first_section_no_above() -> None:
    png = _build_png([((255, 255, 255), 200)])
    sections = [
        _section(node_id="a", y=0, height=100),
        _section(node_id="b", y=100, height=100),
    ]
    result = classify_section_boundaries(sections, global_design_image=png)

    assert result["a"].boundary_above == "unknown"


def test_classify_last_section_no_below() -> None:
    png = _build_png([((255, 255, 255), 200)])
    sections = [
        _section(node_id="a", y=0, height=100),
        _section(node_id="b", y=100, height=100),
    ]
    result = classify_section_boundaries(sections, global_design_image=png)

    assert result["b"].boundary_below == "unknown"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_classify_no_png_returns_unknown_all() -> None:
    sections = [
        _section(node_id="a", y=0, height=100),
        _section(node_id="b", y=100, height=100),
    ]
    result = classify_section_boundaries(sections, global_design_image=None)

    assert all(b.boundary_above == "unknown" for b in result.values())
    assert all(b.boundary_below == "unknown" for b in result.values())
    assert all(b.sampled_top_color is None for b in result.values())
    assert all(b.sampled_bottom_color is None for b in result.values())


def test_classify_section_out_of_bounds() -> None:
    # PNG is only 100px tall, but section claims y=0..200 -> out of bounds -> unknown
    png = _build_png([((255, 0, 0), 100)])
    sections = [
        _section(node_id="a", y=0, height=200),
        _section(node_id="b", y=200, height=100),
    ]
    result = classify_section_boundaries(sections, global_design_image=png)

    assert result["a"].sampled_bottom_color is None
    assert result["b"].sampled_top_color is None
    # Pair walk: missing colors → unknown rather than continuous/hard_break
    assert result["a"].boundary_below == "unknown"
    assert result["b"].boundary_above == "unknown"


def test_classify_records_sampled_colors() -> None:
    # Top band red, bottom band green → both colors recorded on both sections
    png = _build_png([((255, 0, 0), 100), ((0, 255, 0), 100)])
    sections = [
        _section(node_id="a", y=0, height=100),
        _section(node_id="b", y=100, height=100),
    ]
    result = classify_section_boundaries(sections, global_design_image=png)

    assert result["a"].sampled_top_color == "#FF0000"
    assert result["a"].sampled_bottom_color == "#FF0000"
    assert result["b"].sampled_top_color == "#00FF00"
    assert result["b"].sampled_bottom_color == "#00FF00"


# ---------------------------------------------------------------------------
# analyze_layout integration
# ---------------------------------------------------------------------------


def _design_structure_two_sections() -> DesignFileStructure:
    """Two stacked content frames at y=0..100 and y=100..200."""
    sec_a = DesignNode(
        id="a",
        name="section-a",
        type=DesignNodeType.FRAME,
        x=0.0,
        y=0.0,
        width=600.0,
        height=100.0,
    )
    sec_b = DesignNode(
        id="b",
        name="section-b",
        type=DesignNodeType.FRAME,
        x=0.0,
        y=100.0,
        width=600.0,
        height=100.0,
    )
    page = DesignNode(
        id="page-1",
        name="email",
        type=DesignNodeType.PAGE,
        children=[sec_a, sec_b],
    )
    return DesignFileStructure(file_name="test.fig", pages=[page])


def test_layout_analyzer_threads_boundaries() -> None:
    structure = _design_structure_two_sections()
    png = _build_png([((10, 20, 30), 100), ((10, 20, 30), 100)])

    layout = analyze_layout(structure, global_design_image=png)

    by_id = {s.node_id: s for s in layout.sections}
    # Both sections share the solid PNG color → continuous pair
    assert by_id["a"].boundary_below == "continuous_with_below"
    assert by_id["b"].boundary_above == "continuous_with_above"
    # Outer edges have no neighbor
    assert by_id["a"].boundary_above == "unknown"
    assert by_id["b"].boundary_below == "unknown"
    # Sampled colors populated
    assert by_id["a"].sampled_top_color == "#0A141E"
    assert by_id["b"].sampled_bottom_color == "#0A141E"


def test_layout_analyzer_no_png_no_boundaries() -> None:
    structure = _design_structure_two_sections()

    layout = analyze_layout(structure, global_design_image=None)

    for s in layout.sections:
        assert s.boundary_above is None
        assert s.boundary_below is None
        assert s.sampled_top_color is None
        assert s.sampled_bottom_color is None


def test_section_boundary_dataclass_is_frozen() -> None:
    """SectionBoundary is a frozen dataclass — mutation raises."""
    import dataclasses

    sb = SectionBoundary(
        section_node_id="a",
        boundary_above="unknown",
        boundary_below="hard_break",
        sampled_top_color="#000000",
        sampled_bottom_color="#FFFFFF",
    )
    try:
        sb.boundary_above = "continuous_with_above"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("SectionBoundary should be frozen")
