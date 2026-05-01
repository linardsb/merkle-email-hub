"""Wrapper unwrap pre-pass — Phase 50.3, Gap 1.

Validates that ``mj-wrapper`` frames containing ≥2 ``mj-section`` children
expand into one ``EmailSection`` per child, propagating the wrapper fill as
``container_bg`` and recording the wrapper id as ``parent_wrapper_id``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.core.config import get_settings
from app.design_sync.component_matcher import ComponentMatch
from app.design_sync.component_renderer import ComponentRenderer
from app.design_sync.figma.layout_analyzer import (
    EmailSection,
    EmailSectionType,
    NamingConvention,
    analyze_layout,
)
from app.design_sync.protocol import DesignFileStructure, DesignNode, DesignNodeType
from app.design_sync.tests.conftest import make_design_node, make_file_structure


@pytest.fixture(autouse=True)
def _enable_wrapper_unwrap() -> Iterator[None]:
    """Default to ``False`` in production — flip on for the test suite."""
    settings = get_settings()
    original = settings.design_sync.wrapper_unwrap_enabled
    settings.design_sync.wrapper_unwrap_enabled = True
    try:
        yield
    finally:
        settings.design_sync.wrapper_unwrap_enabled = original


def _mj_section(node_id: str, name: str = "mj-section", **overrides: object) -> DesignNode:
    return make_design_node(
        id=node_id,
        name=name,
        type=DesignNodeType.FRAME,
        children=[make_design_node(id=f"{node_id}_text", name="mj-text", text_content="x")],
        **overrides,
    )


def _structure_with_wrapper(wrapper: DesignNode) -> DesignFileStructure:
    """Place a wrapper at page level alongside a decorative sibling.

    The existing single-frame unwrap at ``_get_section_candidates`` would
    consume a lone wrapper by replacing it with its children. Adding a
    sibling keeps the wrapper itself as a candidate so the Phase 50.3
    second-pass receives it.
    """
    sibling = make_design_node(
        id="mj-preheader",
        name="mj-section preheader",
        type=DesignNodeType.FRAME,
        children=[make_design_node(id="ph_text", name="mj-text", text_content="·")],
    )
    return make_file_structure(wrapper, sibling)


class TestWrapperUnwrap:
    def test_unwrap_mjml_wrapper_with_three_sections(self) -> None:
        wrapper = make_design_node(
            id="wrap_1",
            name="mj-wrapper",
            fill_color="#F5F5F5",
            children=[
                _mj_section("sec_1", y=0.0),
                _mj_section("sec_2", y=200.0),
                _mj_section("sec_3", y=400.0),
            ],
        )
        layout = analyze_layout(_structure_with_wrapper(wrapper))

        unwrapped = [s for s in layout.sections if s.parent_wrapper_id == "wrap_1"]
        assert [s.node_id for s in unwrapped] == ["sec_1", "sec_2", "sec_3"]
        assert all(s.container_bg == "#F5F5F5" for s in unwrapped)

    def test_no_unwrap_single_section_wrapper(self) -> None:
        wrapper = make_design_node(
            id="wrap_only",
            name="mj-wrapper",
            fill_color="#FFFFFF",
            children=[_mj_section("only_sec")],
        )
        layout = analyze_layout(_structure_with_wrapper(wrapper))

        # The wrapper itself remains as one section — only one child means the
        # second-pass detector skips it (the threshold is ≥2 section children).
        wrapper_sections = [s for s in layout.sections if s.node_id == "wrap_only"]
        assert len(wrapper_sections) == 1
        assert wrapper_sections[0].container_bg is None
        assert wrapper_sections[0].parent_wrapper_id is None

    def test_no_unwrap_wrapper_without_fill(self) -> None:
        wrapper = make_design_node(
            id="wrap_nofill",
            name="mj-wrapper",
            fill_color=None,
            children=[
                _mj_section("nofill_a"),
                _mj_section("nofill_b"),
            ],
        )
        layout = analyze_layout(_structure_with_wrapper(wrapper))

        # Without a fill, the second-pass detector skips this wrapper. The
        # wrapper stays as one section — its children never surface as
        # individual ``EmailSection`` instances at this scope.
        assert "wrap_nofill" in {s.node_id for s in layout.sections}
        assert all(s.parent_wrapper_id is None for s in layout.sections)
        assert all(s.container_bg is None for s in layout.sections)

    def test_no_unwrap_descriptive_naming(self) -> None:
        # Force descriptive naming via explicit kwarg so the second-pass is
        # gated off even though the wrapper has a fill + ≥2 section children.
        wrapper = make_design_node(
            id="wrap_desc",
            name="HeaderArea",
            fill_color="#000000",
            children=[
                make_design_node(
                    id="hero",
                    name="Hero",
                    children=[
                        make_design_node(id="hero_t", name="Title", text_content="x"),
                    ],
                ),
                make_design_node(
                    id="cta",
                    name="CTA",
                    children=[
                        make_design_node(id="cta_t", name="Button", text_content="x"),
                    ],
                ),
            ],
        )
        layout = analyze_layout(
            _structure_with_wrapper(wrapper),
            naming_convention=NamingConvention.DESCRIPTIVE.value,
        )

        # Descriptive convention does not opt in to the 2nd-pass unwrap.
        assert all(s.container_bg is None for s in layout.sections)
        assert all(s.parent_wrapper_id is None for s in layout.sections)

    def test_wrapper_bg_propagated_to_children(self) -> None:
        wrapper = make_design_node(
            id="wrap_bg",
            name="mj-wrapper",
            fill_color="#1A2B3C",
            children=[
                _mj_section("bg_a"),
                _mj_section("bg_b"),
            ],
        )
        layout = analyze_layout(_structure_with_wrapper(wrapper))

        unwrapped = [s for s in layout.sections if s.parent_wrapper_id == "wrap_bg"]
        assert len(unwrapped) == 2
        for section in unwrapped:
            assert section.container_bg == "#1A2B3C"

    def test_parent_wrapper_id_set(self) -> None:
        wrapper = make_design_node(
            id="parent_wrap_xyz",
            name="mj-wrapper",
            fill_color="#222222",
            children=[
                _mj_section("child_a"),
                _mj_section("child_b"),
            ],
        )
        layout = analyze_layout(_structure_with_wrapper(wrapper))

        unwrapped = [s for s in layout.sections if s.node_id in {"child_a", "child_b"}]
        assert len(unwrapped) == 2
        assert all(s.parent_wrapper_id == "parent_wrap_xyz" for s in unwrapped)

    def test_section_own_bg_distinct_from_container(self) -> None:
        # The white card child has its own fill that must remain in bg_color
        # while container_bg carries the wrapper's grey background.
        wrapper = make_design_node(
            id="wrap_outer",
            name="mj-wrapper",
            fill_color="#EEEEEE",
            children=[
                _mj_section("white_card", fill_color="#FFFFFF"),
                _mj_section("grey_card", fill_color="#DDDDDD"),
            ],
        )
        layout = analyze_layout(_structure_with_wrapper(wrapper))

        by_id = {s.node_id: s for s in layout.sections}
        assert by_id["white_card"].bg_color == "#FFFFFF"
        assert by_id["white_card"].container_bg == "#EEEEEE"
        assert by_id["grey_card"].bg_color == "#DDDDDD"
        assert by_id["grey_card"].container_bg == "#EEEEEE"

    def test_unwrap_disabled_by_flag(self) -> None:
        settings = get_settings()
        settings.design_sync.wrapper_unwrap_enabled = False

        wrapper = make_design_node(
            id="wrap_off",
            name="mj-wrapper",
            fill_color="#ABCDEF",
            children=[
                _mj_section("off_a"),
                _mj_section("off_b"),
            ],
        )
        layout = analyze_layout(_structure_with_wrapper(wrapper))

        # Phase 50.3 propagation is skipped, so the wrapper itself remains as
        # one section with no container_bg or parent_wrapper_id on anything.
        assert "wrap_off" in {s.node_id for s in layout.sections}
        assert all(s.container_bg is None for s in layout.sections)
        assert all(s.parent_wrapper_id is None for s in layout.sections)

    def test_unwrap_preserves_section_order(self) -> None:
        wrapper = make_design_node(
            id="wrap_order",
            name="mj-wrapper",
            fill_color="#101010",
            children=[
                _mj_section("top", y=0.0),
                _mj_section("middle", y=300.0),
                _mj_section("bottom", y=600.0),
            ],
        )
        layout = analyze_layout(_structure_with_wrapper(wrapper))

        unwrapped_ids = [s.node_id for s in layout.sections if s.parent_wrapper_id == "wrap_order"]
        assert unwrapped_ids == ["top", "middle", "bottom"]


class TestRendererEmitsContainerBg:
    def test_renderer_emits_wrapper_bg(self) -> None:
        # Phase 50.4: container_bg flows through the ``_outer`` token override
        # path (built by ``_build_token_overrides``), not the provisional 50.3
        # wrap that used to inject a bare ``<td bgcolor>`` cell.
        from app.design_sync.component_matcher import TokenOverride

        renderer = ComponentRenderer(container_width=600)
        renderer.load()

        section = EmailSection(
            section_type=EmailSectionType.CONTENT,
            node_id="sec_1",
            node_name="mj-section",
            container_bg="#123456",
            parent_wrapper_id="wrap_1",
        )
        match = ComponentMatch(
            section_idx=0,
            section=section,
            component_slug="article-card",
            slot_fills=[],
            token_overrides=[TokenOverride("background-color", "_outer", "#123456")],
        )

        result = renderer.render_section(match)

        # ``_outer`` class targeting injects both the inline style (modern
        # clients) and the bgcolor attribute (Outlook).
        assert "background-color:#123456" in result.html
        assert 'bgcolor="#123456"' in result.html
        # Dark-mode class is still registered for the wrapper bg.
        assert "bgcolor-123456" in result.dark_mode_classes
