"""Tests for content group extraction and slot filling fidelity (49.5)."""

from __future__ import annotations

import logging

import pytest

from app.design_sync.component_matcher import (
    SlotFill,
    _build_slot_fills,
    _log_default_fills,
)
from app.design_sync.component_renderer import _PLACEHOLDER_IN_OUTPUT_RE
from app.design_sync.figma.layout_analyzer import (
    ButtonElement,
    ColumnLayout,
    ContentGroup,
    EmailSection,
    EmailSectionType,
    ImagePlaceholder,
    TextBlock,
    _assign_role_hints,
    _extract_content_groups,
)
from app.design_sync.protocol import DesignNode, DesignNodeType
from app.design_sync.tests.conftest import make_design_node


def _text(
    content: str,
    *,
    node_id: str = "t1",
    font_size: float | None = 14.0,
    is_heading: bool = False,
    role_hint: str | None = None,
    source_frame_id: str | None = None,
) -> TextBlock:
    return TextBlock(
        node_id=node_id,
        content=content,
        font_size=font_size,
        is_heading=is_heading,
        role_hint=role_hint,
        source_frame_id=source_frame_id,
    )


def _image(node_id: str = "img_1", name: str = "photo") -> ImagePlaceholder:
    return ImagePlaceholder(node_id=node_id, node_name=name, width=600, height=400)


def _button(text: str = "Click me") -> ButtonElement:
    return ButtonElement(node_id="btn_1", text=text)


def _make_section(
    section_type: EmailSectionType = EmailSectionType.CONTENT,
    *,
    texts: list[TextBlock] | None = None,
    images: list[ImagePlaceholder] | None = None,
    buttons: list[ButtonElement] | None = None,
    child_content_groups: list[ContentGroup] | None = None,
    column_layout: ColumnLayout = ColumnLayout.SINGLE,
    column_count: int = 1,
    content_roles: tuple[str, ...] = (),
) -> EmailSection:
    return EmailSection(
        section_type=section_type,
        node_id="frame_1",
        node_name="Section",
        texts=texts or [],
        images=images or [],
        buttons=buttons or [],
        child_content_groups=child_content_groups or [],
        column_layout=column_layout,
        column_count=column_count,
        content_roles=content_roles,
    )


def _make_text_node(
    node_id: str,
    text: str,
    *,
    font_size: float = 14.0,
) -> DesignNode:
    """Create a TEXT DesignNode."""
    return make_design_node(
        id=node_id,
        name=f"Text-{node_id}",
        type=DesignNodeType.TEXT,
        text_content=text,
        font_size=font_size,
        width=200.0,
        height=20.0,
    )


class TestContentGroupExtraction:
    """Tests for _extract_content_groups()."""

    def test_single_child_frame_returns_empty(self) -> None:
        """One child frame → not enough structure for grouping."""
        child = make_design_node(
            id="child1",
            name="Block1",
            type=DesignNodeType.FRAME,
            children=[_make_text_node("t1", "Hello")],
        )
        parent = make_design_node(id="parent", name="Section", children=[child])
        result = _extract_content_groups(parent)
        assert result == []

    def test_two_child_frames_returns_two_groups(self) -> None:
        """Two child FRAMEs with TEXT children → 2 ContentGroups."""
        child1 = make_design_node(
            id="child1",
            name="Block1",
            type=DesignNodeType.FRAME,
            children=[_make_text_node("t1", "Heading One", font_size=20.0)],
        )
        child2 = make_design_node(
            id="child2",
            name="Block2",
            type=DesignNodeType.FRAME,
            children=[_make_text_node("t2", "Heading Two", font_size=20.0)],
        )
        parent = make_design_node(id="parent", name="Section", children=[child1, child2])
        result = _extract_content_groups(parent)
        assert len(result) == 2
        assert result[0].frame_node_id == "child1"
        assert result[1].frame_node_id == "child2"
        assert len(result[0].texts) == 1
        assert result[0].texts[0].content == "Heading One"

    def test_deeply_nested_text_extracted(self) -> None:
        """TEXT 3 levels deep inside child frame → still appears in group."""
        inner = make_design_node(
            id="inner",
            name="Inner",
            type=DesignNodeType.FRAME,
            children=[_make_text_node("t_deep", "Deep text")],
        )
        child1 = make_design_node(
            id="child1",
            name="Block1",
            type=DesignNodeType.FRAME,
            children=[inner],
        )
        child2 = make_design_node(
            id="child2",
            name="Block2",
            type=DesignNodeType.FRAME,
            children=[_make_text_node("t2", "Other text")],
        )
        parent = make_design_node(id="parent", name="Section", children=[child1, child2])
        result = _extract_content_groups(parent)
        assert len(result) == 2
        assert result[0].texts[0].content == "Deep text"

    def test_role_hint_heading_largest_font(self) -> None:
        """Group with 24px + 14px + 14px texts → 24px gets heading, 14px gets body."""
        texts = [
            _text("Big Title", font_size=24.0, node_id="t1"),
            _text("Body one", font_size=14.0, node_id="t2"),
            _text("Body two", font_size=14.0, node_id="t3"),
        ]
        result = _assign_role_hints(texts, "frame1")
        assert result[0].role_hint == "heading"
        assert result[1].role_hint == "body"
        assert result[0].source_frame_id == "frame1"

    def test_role_hint_label_small_font(self) -> None:
        """8px text with 24px heading → role_hint='label'."""
        texts = [
            _text("Big", font_size=24.0, node_id="t1"),
            _text("Normal", font_size=14.0, node_id="t2"),
            _text("Normal2", font_size=14.0, node_id="t3"),
            _text("Tiny", font_size=8.0, node_id="t4"),
        ]
        result = _assign_role_hints(texts, "frame1")
        assert result[0].role_hint == "heading"
        assert result[1].role_hint == "body"
        assert result[3].role_hint == "label"

    def test_empty_text_node_skipped(self) -> None:
        """TEXT node with empty characters → not in group."""
        empty = make_design_node(
            id="t_empty",
            name="Empty",
            type=DesignNodeType.TEXT,
            text_content="",
            font_size=14.0,
            width=200.0,
            height=20.0,
        )
        text_node = _make_text_node("t1", "Real content")
        child1 = make_design_node(
            id="child1",
            name="Block1",
            type=DesignNodeType.FRAME,
            children=[empty, text_node],
        )
        child2 = make_design_node(
            id="child2",
            name="Block2",
            type=DesignNodeType.FRAME,
            children=[_make_text_node("t2", "Other")],
        )
        parent = make_design_node(id="parent", name="Section", children=[child1, child2])
        result = _extract_content_groups(parent)
        assert len(result) == 2
        # Empty text should not appear
        assert all(t.content != "" for t in result[0].texts)

    def test_source_frame_id_set(self) -> None:
        """Each TextBlock's source_frame_id matches its parent frame."""
        child1 = make_design_node(
            id="frame_a",
            name="FrameA",
            type=DesignNodeType.FRAME,
            children=[_make_text_node("t1", "Text A")],
        )
        child2 = make_design_node(
            id="frame_b",
            name="FrameB",
            type=DesignNodeType.FRAME,
            children=[_make_text_node("t2", "Text B")],
        )
        parent = make_design_node(id="parent", name="Section", children=[child1, child2])
        result = _extract_content_groups(parent)
        assert result[0].texts[0].source_frame_id == "frame_a"
        assert result[1].texts[0].source_frame_id == "frame_b"


class TestContentGroupSlotFilling:
    """Tests for slot filling with child_content_groups."""

    def test_text_block_uses_first_group_heading(self) -> None:
        """Section with 3 child_content_groups → heading slot = first group's heading."""
        groups = [
            ContentGroup(
                frame_node_id="g1",
                frame_name="Group1",
                texts=[_text("Real Heading", role_hint="heading", font_size=20.0)],
            ),
            ContentGroup(
                frame_node_id="g2",
                frame_name="Group2",
                texts=[_text("Second Heading", role_hint="heading", font_size=20.0)],
            ),
            ContentGroup(
                frame_node_id="g3",
                frame_name="Group3",
                texts=[_text("Third Heading", role_hint="heading", font_size=20.0)],
            ),
        ]
        section = _make_section(child_content_groups=groups)
        fills = _build_slot_fills("text-block", section, 600)
        heading_fill = next((f for f in fills if f.slot_id == "heading"), None)
        assert heading_fill is not None
        assert heading_fill.value == "Real Heading"

    def test_text_block_concatenates_all_bodies(self) -> None:
        """3 groups with body texts → body slot contains all 3 bodies joined."""
        groups = [
            ContentGroup(
                frame_node_id=f"g{i}",
                frame_name=f"Group{i}",
                texts=[
                    _text(f"Heading {i}", role_hint="heading", font_size=20.0, node_id=f"h{i}"),
                    _text(f"Body text {i}", role_hint="body", font_size=14.0, node_id=f"b{i}"),
                ],
            )
            for i in range(1, 4)
        ]
        section = _make_section(child_content_groups=groups)
        fills = _build_slot_fills("text-block", section, 600)
        body_fill = next((f for f in fills if f.slot_id == "body"), None)
        assert body_fill is not None
        assert "Body text 1" in body_fill.value
        assert "Body text 2" in body_fill.value
        assert "Body text 3" in body_fill.value

    def test_hero_uses_content_groups(self) -> None:
        """Hero with child_content_groups → headline from group heading."""
        groups = [
            ContentGroup(
                frame_node_id="g1",
                frame_name="Group1",
                texts=[
                    _text("Hero Title", role_hint="heading", font_size=24.0),
                    _text("Hero subtitle", role_hint="body", font_size=14.0, node_id="b1"),
                ],
            ),
            ContentGroup(
                frame_node_id="g2",
                frame_name="Group2",
                texts=[_text("Extra info", role_hint="body", font_size=14.0, node_id="b2")],
            ),
        ]
        section = _make_section(
            section_type=EmailSectionType.HERO,
            child_content_groups=groups,
        )
        fills = _build_slot_fills("hero-block", section, 600)
        headline = next((f for f in fills if f.slot_id == "headline"), None)
        assert headline is not None
        assert headline.value == "Hero Title"
        subtext = next((f for f in fills if f.slot_id == "subtext"), None)
        assert subtext is not None
        assert subtext.value == "Hero subtitle"

    def test_fallback_to_flat_when_no_groups(self) -> None:
        """Empty child_content_groups → existing flat behavior unchanged."""
        section = _make_section(
            texts=[
                _text("Flat Heading", is_heading=True, font_size=20.0),
                _text("Flat body", font_size=14.0, node_id="b1"),
            ],
        )
        fills = _build_slot_fills("text-block", section, 600)
        heading_fill = next((f for f in fills if f.slot_id == "heading"), None)
        assert heading_fill is not None
        assert heading_fill.value == "Flat Heading"
        body_fill = next((f for f in fills if f.slot_id == "body"), None)
        assert body_fill is not None
        assert body_fill.value == "Flat body"

    def test_placeholder_text_skipped_in_groups(self) -> None:
        """Group with 'Lorem ipsum' text → skipped, non-placeholder used."""
        groups = [
            ContentGroup(
                frame_node_id="g1",
                frame_name="Group1",
                texts=[
                    _text("Real Heading", role_hint="heading", font_size=20.0),
                    _text(
                        "Lorem ipsum dolor sit amet", role_hint="body", font_size=14.0, node_id="p1"
                    ),
                ],
            ),
            ContentGroup(
                frame_node_id="g2",
                frame_name="Group2",
                texts=[
                    _text("Another Heading", role_hint="heading", font_size=20.0, node_id="h2"),
                    _text("Actual content here", role_hint="body", font_size=14.0, node_id="b2"),
                ],
            ),
        ]
        section = _make_section(child_content_groups=groups)
        fills = _build_slot_fills("text-block", section, 600)
        body_fill = next((f for f in fills if f.slot_id == "body"), None)
        assert body_fill is not None
        # Lorem ipsum should be excluded by _bodies_from_groups
        assert "Lorem ipsum" not in body_fill.value
        assert "Actual content here" in body_fill.value


class TestPlaceholderWarning:
    """Tests for placeholder detection warnings."""

    def test_placeholder_in_output_logged(self, caplog: logging.LogCaptureFixture) -> None:
        """Rendered HTML with 'Section Heading' in data-slot → warning logged."""
        test_html = '<td data-slot="heading">Section Heading</td>'
        matches = list(_PLACEHOLDER_IN_OUTPUT_RE.finditer(test_html))
        assert len(matches) == 1
        assert matches[0].group(1) == "heading"

    def test_default_fill_usage_logged(self, capsys: pytest.CaptureFixture[str]) -> None:
        """_log_default_fills() with placeholder value → warning emitted."""
        section = _make_section()
        fills = [SlotFill("body", "Lorem ipsum dolor sit")]
        _log_default_fills("text-block", section, fills)
        captured = capsys.readouterr()
        assert "design_sync.slot_fill.default_used" in captured.out
