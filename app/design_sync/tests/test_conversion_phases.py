"""Per-phase tests for the component-conversion pipeline split (Part B).

Validates each phase of `_convert_with_components` in isolation:
match → (optional tree-bridge) → render → assemble.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.design_sync.compatibility import ConverterCompatibility
from app.design_sync.component_matcher import ComponentMatch, SlotFill
from app.design_sync.conversion_phases import MatchPhase, RenderPhase
from app.design_sync.converter_service import (
    COMPONENT_SHELL,
    ConversionResult,
    DesignConverterService,
)
from app.design_sync.figma.layout_analyzer import (
    ColumnLayout,
    DesignLayoutDescription,
    EmailSection,
    EmailSectionType,
    TextBlock,
)
from app.design_sync.protocol import ExtractedColor, ExtractedTokens, ExtractedTypography

# ── Fixtures ─────────────────────────────────────────────────────────


def _make_section(
    *,
    idx: int = 0,
    section_type: EmailSectionType = EmailSectionType.CONTENT,
    bg_color: str | None = "#ffffff",
    text: str = "Body copy",
) -> EmailSection:
    return EmailSection(
        section_type=section_type,
        node_id=f"node_{idx}",
        node_name=f"Section {idx}",
        texts=[TextBlock(node_id=f"t_{idx}", content=text)],
        column_layout=ColumnLayout.SINGLE,
        column_count=1,
        height=120.0,
        bg_color=bg_color,
    )


def _make_layout(sections: list[EmailSection] | None = None) -> DesignLayoutDescription:
    return DesignLayoutDescription(
        file_name="test.fig",
        overall_width=600.0,
        sections=sections if sections is not None else [_make_section()],
    )


def _make_tokens() -> ExtractedTokens:
    return ExtractedTokens(
        colors=[ExtractedColor(name="background", hex="#ffffff")],
        typography=[
            ExtractedTypography(
                name="body",
                family="Arial",
                weight="400",
                size=16.0,
                line_height=1.4,
            )
        ],
    )


def _make_match(idx: int, section: EmailSection) -> ComponentMatch:
    return ComponentMatch(
        section_idx=idx,
        section=section,
        component_slug="text-block",
        slot_fills=[SlotFill(slot_id="body", value=section.texts[0].content)],
        token_overrides=[],
        confidence=1.0,
    )


@pytest.fixture
def service() -> DesignConverterService:
    return DesignConverterService()


# ── _match_phase ─────────────────────────────────────────────────────


class TestMatchPhase:
    def test_returns_match_for_each_section(self, service: DesignConverterService) -> None:
        layout = _make_layout([_make_section(idx=i) for i in range(3)])
        match = service._match_phase(layout=layout, container_width=600, image_urls=None)

        assert isinstance(match, MatchPhase)
        assert len(match.matches) == 3
        assert all(isinstance(m, ComponentMatch) for m in match.matches)

    def test_empty_layout_yields_empty_matches(self, service: DesignConverterService) -> None:
        layout = _make_layout([])
        match = service._match_phase(layout=layout, container_width=600, image_urls=None)

        assert match.matches == []
        assert match.group_map == {}
        assert match.grouped_sections == []

    def test_group_map_empty_when_sibling_detection_disabled(
        self, service: DesignConverterService
    ) -> None:
        layout = _make_layout([_make_section(idx=i) for i in range(2)])
        with patch("app.design_sync.converter_service.get_settings") as mock_settings:
            mock_settings.return_value.design_sync.sibling_detection_enabled = False
            match = service._match_phase(layout=layout, container_width=600, image_urls=None)

        assert match.group_map == {}


# ── _try_tree_bridge ─────────────────────────────────────────────────


class TestTryTreeBridge:
    def test_returns_none_when_compiler_raises(self, service: DesignConverterService) -> None:
        layout = _make_layout()
        match = MatchPhase(
            matches=[_make_match(0, layout.sections[0])],
            grouped_sections=list(layout.sections),
            group_map={},
        )
        compat = ConverterCompatibility(target_clients=None)

        with patch("app.components.tree_compiler.TreeCompiler") as mock_compiler:
            mock_compiler.return_value.compile.side_effect = RuntimeError("boom")
            result = service._try_tree_bridge(
                layout=layout,
                match=match,
                tokens=_make_tokens(),
                warnings=[],
                compat=compat,
            )

        assert result is None

    def test_returns_conversion_result_on_success(self, service: DesignConverterService) -> None:
        layout = _make_layout()
        match = MatchPhase(
            matches=[_make_match(0, layout.sections[0])],
            grouped_sections=list(layout.sections),
            group_map={},
        )
        compat = ConverterCompatibility(target_clients=None)

        with patch("app.components.tree_compiler.TreeCompiler") as mock_compiler:
            mock_compiler.return_value.compile.return_value.html = "<html>tree</html>"
            result = service._try_tree_bridge(
                layout=layout,
                match=match,
                tokens=_make_tokens(),
                warnings=[],
                compat=compat,
            )

        assert isinstance(result, ConversionResult)
        assert result.html == "<html>tree</html>"
        assert result.tree is not None


# ── _render_phase ────────────────────────────────────────────────────


class TestRenderPhase:
    def test_renders_each_match_into_section_parts(self, service: DesignConverterService) -> None:
        layout = _make_layout([_make_section(idx=i) for i in range(2)])
        matches = [_make_match(i, s) for i, s in enumerate(layout.sections)]
        match = MatchPhase(matches=matches, grouped_sections=list(layout.sections), group_map={})

        render = service._render_phase(
            match=match,
            tokens=_make_tokens(),
            warnings=[],
            container_width=600,
            connection_id=None,
            section_hashes=None,
        )

        assert isinstance(render, RenderPhase)
        assert len(render.section_parts) == 2
        # No cache, so every render is a miss
        assert render.miss_count == 2
        assert render.hit_count == 0

    def test_empty_matches_returns_empty_render(self, service: DesignConverterService) -> None:
        match = MatchPhase(matches=[], grouped_sections=[], group_map={})

        render = service._render_phase(
            match=match,
            tokens=_make_tokens(),
            warnings=[],
            container_width=600,
            connection_id=None,
            section_hashes=None,
        )

        assert render.section_parts == []
        assert render.images == []
        assert render.miss_count == 0
        assert render.hit_count == 0


# ── _assemble_phase ──────────────────────────────────────────────────


class TestAssemblePhase:
    def test_wraps_section_parts_in_component_shell(self, service: DesignConverterService) -> None:
        layout = _make_layout([_make_section(idx=0)])
        match = MatchPhase(
            matches=[_make_match(0, layout.sections[0])],
            grouped_sections=list(layout.sections),
            group_map={},
        )
        render = RenderPhase(
            section_parts=["<table><tr><td>SENTINEL</td></tr></table>"],
            images=[],
            hit_count=0,
            miss_count=1,
            warnings=[],
        )
        compat = ConverterCompatibility(target_clients=None)

        result = service._assemble_phase(
            match=match,
            render=render,
            layout=layout,
            tokens=_make_tokens(),
            compat=compat,
            container_width=600,
            connection_id=None,
            section_hashes=None,
        )

        assert isinstance(result, ConversionResult)
        assert "SENTINEL" in result.html
        # Shell sentinel: dark-bg class is unique to COMPONENT_SHELL
        assert 'class="dark-bg"' in result.html
        assert result.sections_count == 1

    def test_cache_hit_rate_emitted_when_connection_id_set(
        self, service: DesignConverterService
    ) -> None:
        layout = _make_layout([_make_section(idx=0)])
        match = MatchPhase(
            matches=[_make_match(0, layout.sections[0])],
            grouped_sections=list(layout.sections),
            group_map={},
        )
        render = RenderPhase(
            section_parts=["<table></table>"],
            images=[],
            hit_count=3,
            miss_count=1,
            warnings=[],
        )

        result = service._assemble_phase(
            match=match,
            render=render,
            layout=layout,
            tokens=_make_tokens(),
            compat=ConverterCompatibility(target_clients=None),
            container_width=600,
            connection_id="conn-1",
            section_hashes={"node_0": "hash"},
        )

        assert result.cache_hit_rate == pytest.approx(0.75)  # pyright: ignore[reportUnknownMemberType]

    def test_compatibility_hints_included(self, service: DesignConverterService) -> None:
        layout = _make_layout([_make_section(idx=0)])
        match = MatchPhase(
            matches=[_make_match(0, layout.sections[0])],
            grouped_sections=list(layout.sections),
            group_map={},
        )
        render = RenderPhase(
            section_parts=["<table></table>"], images=[], hit_count=0, miss_count=1, warnings=[]
        )
        compat = ConverterCompatibility(target_clients=["outlook"])

        result = service._assemble_phase(
            match=match,
            render=render,
            layout=layout,
            tokens=_make_tokens(),
            compat=compat,
            container_width=600,
            connection_id=None,
            section_hashes=None,
        )

        # max-width was warned during assemble (compat has targets)
        assert result.compatibility_hints == compat.hints


# ── Orchestrator integration ─────────────────────────────────────────


class TestOrchestrator:
    def test_legacy_path_returns_html_result(self, service: DesignConverterService) -> None:
        layout = _make_layout([_make_section(idx=0, section_type=EmailSectionType.HERO)])
        compat = ConverterCompatibility(target_clients=None)

        result = service._convert_with_components(
            _frames=[],
            layout=layout,
            tokens=_make_tokens(),
            warnings=[],
            compat=compat,
            container_width=600,
        )

        assert isinstance(result, ConversionResult)
        assert result.sections_count == 1
        # Orchestrator went through _assemble_phase
        assert 'class="dark-bg"' in result.html

    def test_tree_bridge_falls_through_to_legacy_on_failure(
        self, service: DesignConverterService
    ) -> None:
        layout = _make_layout([_make_section(idx=0)])
        compat = ConverterCompatibility(target_clients=None)

        with (
            patch("app.design_sync.converter_service.get_settings") as mock_settings,
            patch("app.components.tree_compiler.TreeCompiler") as mock_compiler,
        ):
            ds = mock_settings.return_value.design_sync
            ds.sibling_detection_enabled = False
            ds.tree_bridge_enabled = True
            ds.bgcolor_propagation_enabled = False
            ds.section_cache_enabled = False
            ds.custom_component_enabled = False
            ds.custom_component_max_per_email = 0
            ds.custom_component_confidence_threshold = 0.0
            mock_compiler.return_value.compile.side_effect = RuntimeError("compiler down")

            result = service._convert_with_components(
                _frames=[],
                layout=layout,
                tokens=_make_tokens(),
                warnings=[],
                compat=compat,
                container_width=600,
                output_format="tree",
            )

        # Fell through to legacy renderer — final HTML is the COMPONENT_SHELL, not tree HTML
        assert 'class="dark-bg"' in result.html
        # tree dict is None on the legacy fall-through path
        assert result.tree is None


def test_component_shell_sentinel_exists() -> None:
    """Guards the assembly-phase sentinel used in TestAssemblePhase."""
    assert 'class="dark-bg"' in COMPONENT_SHELL
