"""Tests for 49.7: CTA fidelity — button color/shape extraction and rendering."""

from __future__ import annotations

import pytest

from app.design_sync.component_matcher import (
    ComponentMatch,
    SlotFill,
    TokenOverride,
    _build_column_fill_html,
    match_section,
)
from app.design_sync.component_renderer import ComponentRenderer
from app.design_sync.figma.layout_analyzer import (
    ButtonElement,
    ColumnGroup,
    EmailSection,
    EmailSectionType,
    ImagePlaceholder,
    TextBlock,
)
from app.design_sync.protocol import DesignNode, DesignNodeType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _button(
    text: str = "Shop Now",
    *,
    fill_color: str | None = None,
    text_color: str | None = None,
    border_radius: float | None = None,
    stroke_color: str | None = None,
    stroke_weight: float | None = None,
    url: str | None = "https://example.com",
) -> ButtonElement:
    return ButtonElement(
        node_id="btn_1",
        text=text,
        width=220,
        height=48,
        fill_color=fill_color,
        url=url,
        border_radius=border_radius,
        text_color=text_color,
        stroke_color=stroke_color,
        stroke_weight=stroke_weight,
    )


def _make_section(
    section_type: EmailSectionType = EmailSectionType.CTA,
    *,
    buttons: list[ButtonElement] | None = None,
    texts: list[TextBlock] | None = None,
    images: list[ImagePlaceholder] | None = None,
    bg_color: str | None = None,
) -> EmailSection:
    return EmailSection(
        section_type=section_type,
        node_id="frame_1",
        node_name="CTA Section",
        texts=texts or [],
        images=images or [],
        buttons=buttons or [],
        bg_color=bg_color,
    )


def _make_match(
    slug: str,
    *,
    fills: list[SlotFill] | None = None,
    overrides: list[TokenOverride] | None = None,
    section: EmailSection | None = None,
) -> ComponentMatch:
    return ComponentMatch(
        section_idx=0,
        section=section or _make_section(),
        component_slug=slug,
        slot_fills=fills or [],
        token_overrides=overrides or [],
    )


@pytest.fixture
def renderer() -> ComponentRenderer:
    r = ComponentRenderer(container_width=600)
    r.load()
    return r


# ---------------------------------------------------------------------------
# 1. ButtonElement dataclass fields
# ---------------------------------------------------------------------------


class TestButtonElementFields:
    def test_stroke_fields_default_none(self) -> None:
        btn = ButtonElement(node_id="b1", text="Go")
        assert btn.stroke_color is None
        assert btn.stroke_weight is None
        assert btn.icon_node_id is None

    def test_stroke_fields_populated(self) -> None:
        btn = ButtonElement(
            node_id="b1",
            text="Go",
            stroke_color="#ff0000",
            stroke_weight=2.0,
            icon_node_id="icon_node_1",
        )
        assert btn.stroke_color == "#ff0000"
        assert btn.stroke_weight == 2.0
        assert btn.icon_node_id == "icon_node_1"


# ---------------------------------------------------------------------------
# 2-4. Button extraction from DesignNode
# ---------------------------------------------------------------------------


def _make_button_node(
    *,
    name: str = "CTA Button",
    fill_color: str | None = "#c6fc6a",
    text_color: str | None = "#000000",
    corner_radius: float | None = 6.0,
    stroke_color: str | None = None,
    stroke_weight: float | None = None,
    icon_child: bool = False,
) -> DesignNode:
    """Build a minimal DesignNode tree that _walk_for_buttons will recognise."""
    children: list[DesignNode] = [
        DesignNode(
            id="text_1",
            name="Label",
            type=DesignNodeType.TEXT,
            text_content="Shop Now",
            text_color=text_color,
            width=100,
            height=20,
        ),
    ]
    if icon_child:
        children.append(
            DesignNode(
                id="icon_1",
                name="arrow-icon",
                type=DesignNodeType.VECTOR,
                width=24,
                height=24,
            )
        )
    return DesignNode(
        id="btn_frame",
        name=name,
        type=DesignNodeType.FRAME,
        width=220,
        height=48,
        fill_color=fill_color,
        corner_radius=corner_radius,
        stroke_color=stroke_color,
        stroke_weight=stroke_weight,
        children=children,
    )


class TestButtonExtraction:
    def test_extract_fill_color(self) -> None:
        from app.design_sync.figma.layout_analyzer import _walk_for_buttons

        node = _make_button_node(fill_color="#c6fc6a")
        results: list[ButtonElement] = []
        _walk_for_buttons(node, results)
        assert len(results) == 1
        assert results[0].fill_color == "#c6fc6a"

    def test_extract_stroke_properties(self) -> None:
        from app.design_sync.figma.layout_analyzer import _walk_for_buttons

        node = _make_button_node(stroke_color="#333333", stroke_weight=2.0)
        results: list[ButtonElement] = []
        _walk_for_buttons(node, results)
        assert len(results) == 1
        assert results[0].stroke_color == "#333333"
        assert results[0].stroke_weight == 2.0

    def test_extract_icon_child(self) -> None:
        from app.design_sync.figma.layout_analyzer import _walk_for_buttons

        node = _make_button_node(icon_child=True)
        results: list[ButtonElement] = []
        _walk_for_buttons(node, results)
        assert len(results) == 1
        assert results[0].icon_node_id == "icon_1"

    def test_no_icon_when_absent(self) -> None:
        from app.design_sync.figma.layout_analyzer import _walk_for_buttons

        node = _make_button_node(icon_child=False)
        results: list[ButtonElement] = []
        _walk_for_buttons(node, results)
        assert len(results) == 1
        assert results[0].icon_node_id is None


# ---------------------------------------------------------------------------
# 5-9. CTA token overrides via match_section
# ---------------------------------------------------------------------------


class TestCTATokenOverrides:
    def test_cta_bg_color_override(self) -> None:
        s = _make_section(buttons=[_button(fill_color="#c6fc6a")])
        m = match_section(s, 0)
        bg = [
            o
            for o in m.token_overrides
            if o.target_class == "_cta" and o.css_property == "background-color"
        ]
        assert len(bg) == 1
        assert bg[0].value == "#c6fc6a"

    def test_cta_text_color_override(self) -> None:
        s = _make_section(buttons=[_button(text_color="#000000")])
        m = match_section(s, 0)
        color = [
            o for o in m.token_overrides if o.target_class == "_cta" and o.css_property == "color"
        ]
        assert len(color) == 1
        assert color[0].value == "#000000"

    def test_cta_border_radius_override(self) -> None:
        s = _make_section(buttons=[_button(border_radius=6.0)])
        m = match_section(s, 0)
        radius = [
            o
            for o in m.token_overrides
            if o.target_class == "_cta" and o.css_property == "border-radius"
        ]
        assert len(radius) == 1
        assert radius[0].value == "6px"

    def test_cta_stroke_override(self) -> None:
        s = _make_section(buttons=[_button(stroke_color="#ff0000", stroke_weight=2.0)])
        m = match_section(s, 0)
        border_color = [
            o
            for o in m.token_overrides
            if o.target_class == "_cta" and o.css_property == "border-color"
        ]
        border_width = [
            o
            for o in m.token_overrides
            if o.target_class == "_cta" and o.css_property == "border-width"
        ]
        assert len(border_color) == 1
        assert border_color[0].value == "#ff0000"
        assert len(border_width) == 1
        assert border_width[0].value == "2px"

    def test_no_cta_override_when_missing(self) -> None:
        s = _make_section(buttons=[_button()])
        m = match_section(s, 0)
        cta = [o for o in m.token_overrides if o.target_class == "_cta"]
        assert len(cta) == 0


# ---------------------------------------------------------------------------
# 10-12. Renderer CTA token override application
# ---------------------------------------------------------------------------


class TestRendererCTAOverrides:
    def test_cta_bg_color_applied(self, renderer: ComponentRenderer) -> None:
        match = _make_match(
            "cta-button",
            overrides=[TokenOverride("background-color", "_cta", "#c6fc6a")],
        )
        result = renderer.render_section(match)
        assert (
            "background-color:#c6fc6a" in result.html or "background-color: #c6fc6a" in result.html
        )
        # VML fillcolor
        assert 'fillcolor="#c6fc6a"' in result.html

    def test_cta_border_radius_applied(self, renderer: ComponentRenderer) -> None:
        match = _make_match(
            "cta-button",
            overrides=[TokenOverride("border-radius", "_cta", "6px")],
        )
        result = renderer.render_section(match)
        assert "border-radius:6px" in result.html
        # VML arcsize updated
        assert "arcsize=" in result.html

    def test_cta_text_color_applied(self, renderer: ComponentRenderer) -> None:
        match = _make_match(
            "cta-button",
            overrides=[TokenOverride("color", "_cta", "#000000")],
        )
        result = renderer.render_section(match)
        assert "color:#000000" in result.html


# ---------------------------------------------------------------------------
# 13-14. Column fill uses button properties
# ---------------------------------------------------------------------------


class TestColumnFillButtonProperties:
    def test_column_fill_uses_button_text_color(self) -> None:
        btn = _button(fill_color="#c6fc6a", text_color="#112233")
        group = ColumnGroup(
            column_idx=0,
            node_id="col_1",
            node_name="Column",
            texts=[],
            images=[],
            buttons=[btn],
        )
        html = _build_column_fill_html(group)
        assert "color:#112233" in html

    def test_column_fill_uses_button_radius(self) -> None:
        btn = _button(fill_color="#c6fc6a", border_radius=12.0)
        group = ColumnGroup(
            column_idx=0,
            node_id="col_1",
            node_name="Column",
            texts=[],
            images=[],
            buttons=[btn],
        )
        html = _build_column_fill_html(group)
        assert "border-radius:12px" in html

    def test_column_fill_uses_stroke(self) -> None:
        btn = _button(
            fill_color="#c6fc6a",
            stroke_color="#333333",
            stroke_weight=2.0,
        )
        group = ColumnGroup(
            column_idx=0,
            node_id="col_1",
            node_name="Column",
            texts=[],
            images=[],
            buttons=[btn],
        )
        html = _build_column_fill_html(group)
        assert "border:2px solid #333333" in html


# ---------------------------------------------------------------------------
# 15. Multiple CTAs with different colors
# ---------------------------------------------------------------------------


class TestMultipleCTAs:
    def test_different_cta_colors_per_section(self, renderer: ComponentRenderer) -> None:
        colors = ["#c6fc6a", "#ffbaf3", "#06d5ff"]
        for color in colors:
            match = _make_match(
                "cta-button",
                overrides=[TokenOverride("background-color", "_cta", color)],
            )
            result = renderer.render_section(match)
            assert f'fillcolor="{color}"' in result.html
            assert f"background-color:{color}" in result.html
