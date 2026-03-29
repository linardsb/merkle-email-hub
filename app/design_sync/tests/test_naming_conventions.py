"""Tests for naming convention detection and MJML-aware section classification."""

from __future__ import annotations

import pytest

from app.design_sync.figma.layout_analyzer import (
    EmailSectionType,
    NamingConvention,
    _classify_by_content,
    _classify_mj_section,
    _detect_naming_convention,
    _is_generic_name,
    analyze_layout,
)
from app.design_sync.protocol import DesignFileStructure, DesignNode, DesignNodeType


def _node(
    name: str,
    *,
    ntype: DesignNodeType = DesignNodeType.FRAME,
    children: list[DesignNode] | None = None,
    width: float | None = 600,
    height: float | None = 200,
    x: float | None = 0,
    y: float | None = 0,
    text_content: str | None = None,
    fill_color: str | None = None,
    font_size: float | None = None,
    layout_mode: str | None = None,
    image_ref: str | None = None,
) -> DesignNode:
    return DesignNode(
        id=f"id-{name}",
        name=name,
        type=ntype,
        children=children or [],
        width=width,
        height=height,
        x=x,
        y=y,
        text_content=text_content,
        fill_color=fill_color,
        font_size=font_size,
        layout_mode=layout_mode,
        image_ref=image_ref,
    )


def _text_node(name: str, text: str, *, font_size: float = 16, y: float = 0) -> DesignNode:
    return _node(
        name,
        ntype=DesignNodeType.TEXT,
        text_content=text,
        width=200,
        height=font_size * 1.5,
        y=y,
        font_size=font_size,
    )


def _image_node(name: str, *, width: float = 300, height: float = 200) -> DesignNode:
    return _node(name, ntype=DesignNodeType.IMAGE, width=width, height=height)


def _make_structure(sections: list[DesignNode]) -> DesignFileStructure:
    """Wrap section nodes in a page."""
    page = _node("Page 1", ntype=DesignNodeType.PAGE, children=sections, height=None)
    return DesignFileStructure(file_name="test.fig", pages=[page])


# ── Convention Detection ──


class TestDetectNamingConvention:
    def test_mjml_convention_detected(self) -> None:
        candidates = [
            _node("mj-wrapper", children=[_node("mj-section")]),
            _node("mj-section", children=[_node("mj-column"), _node("mj-column")]),
            _node("mj-section", children=[_node("mj-image"), _node("mj-text")]),
        ]
        assert _detect_naming_convention(candidates) == NamingConvention.MJML

    def test_descriptive_convention_detected(self) -> None:
        candidates = [
            _node("Header"),
            _node("Hero Section"),
            _node("Footer"),
            _node("Content Block"),
        ]
        assert _detect_naming_convention(candidates) == NamingConvention.DESCRIPTIVE

    def test_generic_convention_detected(self) -> None:
        candidates = [
            _node("Frame 1", children=[_node("Frame 2")]),
            _node("Frame 3", children=[_node("Group 1")]),
            _node("Frame 4", children=[_node("Frame 5")]),
        ]
        assert _detect_naming_convention(candidates) == NamingConvention.GENERIC

    def test_mixed_falls_to_descriptive(self) -> None:
        candidates = [
            _node("Header"),
            _node("Frame 1"),
            _node("Hero"),
        ]
        assert _detect_naming_convention(candidates) == NamingConvention.DESCRIPTIVE


class TestIsGenericName:
    @pytest.mark.parametrize(
        "name",
        ["Frame 1", "Group 2", "Rectangle 3", "text 4", "instance 5", "frame", "group"],
    )
    def test_generic_names(self, name: str) -> None:
        assert _is_generic_name(name) is True

    @pytest.mark.parametrize(
        "name",
        ["mj-section", "Hero Section", "Footer", "my-header", "content-block"],
    )
    def test_non_generic_names(self, name: str) -> None:
        assert _is_generic_name(name) is False


# ── MJML Section Classification ──


class TestClassifyMjSection:
    def test_mj_hero_direct(self) -> None:
        node = _node("mj-hero")
        assert _classify_mj_section(node, 0, 5) == EmailSectionType.HERO

    def test_mj_navbar_direct(self) -> None:
        node = _node("mj-navbar")
        assert _classify_mj_section(node, 0, 5) == EmailSectionType.NAV

    def test_mj_section_with_social_child(self) -> None:
        node = _node("mj-section", children=[_node("mj-social")])
        assert _classify_mj_section(node, 3, 5) == EmailSectionType.SOCIAL

    def test_mj_section_with_divider_child(self) -> None:
        node = _node("mj-section", children=[_node("mj-divider")])
        assert _classify_mj_section(node, 2, 5) == EmailSectionType.DIVIDER

    def test_mj_section_with_spacer_child(self) -> None:
        node = _node("mj-section", children=[_node("mj-spacer")])
        assert _classify_mj_section(node, 2, 5) == EmailSectionType.SPACER

    def test_mj_section_with_image_text_button(self) -> None:
        node = _node(
            "mj-section",
            children=[
                _node(
                    "mj-column",
                    children=[
                        _node("mj-image"),
                        _node("mj-text"),
                        _node("mj-button"),
                    ],
                ),
            ],
        )
        assert _classify_mj_section(node, 1, 5) == EmailSectionType.CONTENT

    def test_mj_wrapper_defaults_to_content(self) -> None:
        node = _node("mj-wrapper")
        assert _classify_mj_section(node, 1, 5) == EmailSectionType.CONTENT

    def test_mj_section_large_image_only_is_hero(self) -> None:
        big_img = _node("img", ntype=DesignNodeType.IMAGE, width=500, height=400)
        node_with_img = _node(
            "mj-section",
            children=[big_img],
            width=600,
        )
        assert _classify_mj_section(node_with_img, 0, 5) == EmailSectionType.HERO


# ── Content-Based Classification ──


class TestClassifyByContent:
    def test_large_image_at_top_is_hero(self) -> None:
        from app.design_sync.figma.layout_analyzer import ImagePlaceholder

        big_img = _node("img", ntype=DesignNodeType.IMAGE, width=500, height=400)
        big_img_placeholder = ImagePlaceholder(
            node_id=big_img.id, node_name=big_img.name, width=500, height=400
        )
        node = _node("Frame 1", children=[big_img], width=600)
        result = _classify_by_content(node, [], [big_img_placeholder], [], 0, 5)
        # _has_large_image_child checks direct children
        assert result == EmailSectionType.HERO

    def test_text_button_at_top_with_heading_is_hero(self) -> None:
        from app.design_sync.figma.layout_analyzer import ButtonElement, TextBlock

        texts = [TextBlock(node_id="t1", content="Big Title", font_size=36)]
        buttons = [ButtonElement(node_id="b1", text="Shop Now", width=200, height=48)]
        node = _node("Frame 1")
        result = _classify_by_content(node, texts, [], buttons, 1, 5)
        assert result == EmailSectionType.HERO

    def test_small_text_at_bottom_is_footer(self) -> None:
        from app.design_sync.figma.layout_analyzer import TextBlock

        texts = [
            TextBlock(node_id="t1", content="Unsubscribe", font_size=10),
            TextBlock(node_id="t2", content="© 2026", font_size=11),
        ]
        node = _node("Frame 1")
        result = _classify_by_content(node, texts, [], [], 4, 5)
        assert result == EmailSectionType.FOOTER

    def test_many_short_texts_is_nav(self) -> None:
        from app.design_sync.figma.layout_analyzer import TextBlock

        texts = [TextBlock(node_id=f"t{i}", content=f"Link {i}", font_size=14) for i in range(5)]
        node = _node("Frame 1")
        result = _classify_by_content(node, texts, [], [], 2, 5)
        assert result == EmailSectionType.NAV


# ── Full Pipeline with MJML Naming ──


class TestAnalyzeLayoutMjml:
    def test_mjml_sections_classified(self) -> None:
        sections = [
            _node(
                "mj-wrapper",
                y=0,
                height=80,
                children=[
                    _node("mj-section", children=[_node("mj-navbar")]),
                ],
            ),
            _node(
                "mj-section",
                y=80,
                height=400,
                children=[
                    _node(
                        "mj-column",
                        children=[
                            _node("mj-image", ntype=DesignNodeType.IMAGE, width=500, height=300),
                            _text_node("mj-text", "Welcome", font_size=32),
                            _node(
                                "mj-button",
                                children=[
                                    _text_node("btn-text", "Shop Now", font_size=14),
                                ],
                                height=48,
                                fill_color="#FF0000",
                            ),
                        ],
                    ),
                ],
            ),
            _node(
                "mj-section",
                y=480,
                height=200,
                children=[
                    _node("mj-column", children=[_text_node("mj-text", "Body text")]),
                ],
            ),
            _node("mj-section", y=680, height=60, children=[_node("mj-social")]),
            _node(
                "mj-section",
                y=740,
                height=100,
                children=[
                    _node(
                        "mj-column",
                        children=[
                            _text_node("mj-text", "© 2026 Company", font_size=10),
                        ],
                    ),
                ],
            ),
        ]
        structure = _make_structure(sections)
        layout = analyze_layout(structure)

        assert len(layout.sections) == 5
        types = [s.section_type for s in layout.sections]
        # First section has mj-navbar child → NAV
        assert types[0] == EmailSectionType.NAV
        # Second section has image+text+button → CONTENT
        assert types[1] == EmailSectionType.CONTENT
        # Third is plain content
        assert types[2] == EmailSectionType.CONTENT
        # Fourth has social → SOCIAL
        assert types[3] == EmailSectionType.SOCIAL

    def test_mjml_forced_convention(self) -> None:
        """Forcing naming_convention='mjml' works even with descriptive names."""
        sections = [
            _node("Header", y=0, height=100, children=[_node("mj-navbar")]),
        ]
        structure = _make_structure(sections)
        layout = analyze_layout(structure, naming_convention="mjml")
        assert layout.sections[0].section_type == EmailSectionType.NAV


# ── Custom Name Map ──


class TestCustomNameMap:
    def test_custom_section_map(self) -> None:
        sections = [
            _node("edm-hero-banner", y=0, height=400),
            _node("edm-footer", y=400, height=100),
        ]
        structure = _make_structure(sections)
        layout = analyze_layout(
            structure,
            naming_convention="custom",
            section_name_map={
                "edm-hero-banner": "hero",
                "edm-footer": "footer",
            },
        )
        assert layout.sections[0].section_type == EmailSectionType.HERO
        assert layout.sections[1].section_type == EmailSectionType.FOOTER


# ── Generic Names Content Heuristics ──


class TestGenericNamesAnalysis:
    def test_generic_names_use_content_heuristics(self) -> None:
        big_img = _node("img", ntype=DesignNodeType.IMAGE, width=500, height=400)
        sections = [
            _node(
                "Frame 1",
                y=0,
                height=80,
                children=[
                    _text_node("Text 1", "Home", y=10, font_size=14),
                    _text_node("Text 2", "Shop", y=10, font_size=14),
                    _text_node("Text 3", "About", y=10, font_size=14),
                    _text_node("Text 4", "Contact", y=10, font_size=14),
                ],
            ),
            _node("Frame 2", y=80, height=400, children=[big_img], width=600),
        ]
        structure = _make_structure(sections)
        layout = analyze_layout(structure, naming_convention="generic")

        # Frame 1 has 4 short texts → NAV
        assert layout.sections[0].section_type == EmailSectionType.NAV
        # Frame 2 has large image only → HERO
        assert layout.sections[1].section_type == EmailSectionType.HERO
