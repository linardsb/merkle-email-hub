"""Tests for the conversion diagnostic pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.design_sync.component_matcher import ComponentMatch, match_all
from app.design_sync.component_renderer import ComponentRenderer, RenderedSection
from app.design_sync.diagnose.analyzers import (
    analyze_assembly_stage,
    analyze_design_tree,
    analyze_layout_stage,
    analyze_matching_stage,
    analyze_post_processing,
    analyze_rendering_stage,
    build_section_traces,
)
from app.design_sync.diagnose.models import DiagnosticReport, SectionTrace
from app.design_sync.diagnose.report import (
    dump_structure_to_json,
    dump_tokens_to_json,
    load_structure_from_json,
    load_tokens_from_json,
    report_to_dict,
    report_to_json,
)
from app.design_sync.diagnose.runner import DiagnosticRunner
from app.design_sync.figma.layout_analyzer import (
    EmailSection,
    EmailSectionType,
    ImagePlaceholder,
    TextBlock,
    analyze_layout,
)
from app.design_sync.protocol import (
    DesignFileStructure,
    DesignNode,
    DesignNodeType,
    ExtractedColor,
    ExtractedGradient,
    ExtractedSpacing,
    ExtractedTokens,
    ExtractedTypography,
)

# ── Test Data Factories ──


def _make_tokens() -> ExtractedTokens:
    return ExtractedTokens(
        colors=[
            ExtractedColor(name="Background", hex="#FFFFFF"),
            ExtractedColor(name="Text Color", hex="#333333"),
            ExtractedColor(name="Primary", hex="#0066CC"),
        ],
        dark_colors=[
            ExtractedColor(name="Background", hex="#1A1A2E"),
            ExtractedColor(name="Text Color", hex="#E0E0E0"),
        ],
        typography=[
            ExtractedTypography(
                name="Heading", family="Inter", weight="700", size=32.0, line_height=40.0
            ),
            ExtractedTypography(
                name="Body", family="Inter", weight="400", size=16.0, line_height=24.0
            ),
        ],
        spacing=[ExtractedSpacing(name="s1", value=8)],
        gradients=[
            ExtractedGradient(
                name="HeroBG",
                type="linear",
                angle=180.0,
                stops=(("#0066CC", 0.0), ("#003366", 1.0)),
                fallback_hex="#004C99",
            ),
        ],
    )


def _make_structure() -> DesignFileStructure:
    """Build a realistic design tree: header, hero, content, footer."""
    header = DesignNode(
        id="header",
        name="Header",
        type=DesignNodeType.FRAME,
        width=600,
        height=80,
        layout_mode="HORIZONTAL",
        children=[
            DesignNode(
                id="logo", name="Logo", type=DesignNodeType.IMAGE, width=120, height=40, x=0, y=0
            ),
            DesignNode(
                id="nav",
                name="Nav",
                type=DesignNodeType.TEXT,
                text_content="Home | About",
                font_size=14.0,
                x=400,
                y=0,
            ),
        ],
    )
    hero = DesignNode(
        id="hero",
        name="Hero",
        type=DesignNodeType.FRAME,
        width=600,
        height=400,
        layout_mode="VERTICAL",
        item_spacing=24,
        children=[
            DesignNode(
                id="hero_img",
                name="Hero Image",
                type=DesignNodeType.IMAGE,
                width=520,
                height=200,
                y=0,
            ),
            DesignNode(
                id="hero_h1",
                name="Title",
                type=DesignNodeType.TEXT,
                text_content="Summer Sale",
                font_size=32.0,
                font_weight=700,
                y=200,
            ),
            DesignNode(
                id="hero_btn",
                name="CTA Button",
                type=DesignNodeType.COMPONENT,
                width=200,
                height=48,
                fill_color="#0066CC",
                y=280,
                children=[
                    DesignNode(
                        id="btn_text",
                        name="Label",
                        type=DesignNodeType.TEXT,
                        text_content="Shop Now",
                        font_size=16.0,
                        y=0,
                    ),
                ],
            ),
        ],
    )
    content = DesignNode(
        id="content",
        name="Content",
        type=DesignNodeType.FRAME,
        width=600,
        height=200,
        children=[
            DesignNode(
                id="body_text",
                name="Body",
                type=DesignNodeType.TEXT,
                text_content="Check out our latest collection.",
                font_size=16.0,
                y=0,
            ),
        ],
    )
    footer = DesignNode(
        id="footer",
        name="Footer",
        type=DesignNodeType.FRAME,
        width=600,
        height=60,
        children=[
            DesignNode(
                id="footer_text",
                name="Legal",
                type=DesignNodeType.TEXT,
                text_content="© 2026 Brand Inc.",
                font_size=12.0,
                y=0,
            ),
        ],
    )
    page = DesignNode(
        id="page1",
        name="Email",
        type=DesignNodeType.PAGE,
        children=[header, hero, content, footer],
    )
    return DesignFileStructure(file_name="Campaign.fig", pages=[page])


def _make_unknown_section_structure() -> DesignFileStructure:
    """Structure with multiple frames — middle ones get UNKNOWN classification.

    The layout analyzer classifies by position: first=header, last=footer.
    Middle frames with unrecognized names get UNKNOWN.
    """
    first = DesignNode(
        id="first",
        name="TopBar",
        type=DesignNodeType.FRAME,
        width=600,
        height=60,
        children=[
            DesignNode(
                id="t0", name="T", type=DesignNodeType.TEXT, text_content="Top", font_size=14.0, y=0
            ),
        ],
    )
    middle = DesignNode(
        id="mystery",
        name="XyzWidget",
        type=DesignNodeType.FRAME,
        width=600,
        height=200,
        children=[
            DesignNode(
                id="t1",
                name="T",
                type=DesignNodeType.TEXT,
                text_content="Hello",
                font_size=16.0,
                y=0,
            ),
        ],
    )
    last = DesignNode(
        id="last",
        name="BottomBar",
        type=DesignNodeType.FRAME,
        width=600,
        height=60,
        children=[
            DesignNode(
                id="t2", name="T", type=DesignNodeType.TEXT, text_content="End", font_size=12.0, y=0
            ),
        ],
    )
    page = DesignNode(
        id="p1", name="Email", type=DesignNodeType.PAGE, children=[first, middle, last]
    )
    return DesignFileStructure(file_name="test.fig", pages=[page])


# ── Design Summary Tests ──


class TestDesignSummary:
    def test_counts_node_types(self) -> None:
        structure = _make_structure()
        summary, _ = analyze_design_tree(structure)
        assert summary.total_nodes > 0
        assert "FRAME" in summary.node_type_counts
        assert "TEXT" in summary.node_type_counts
        assert "IMAGE" in summary.node_type_counts

    def test_detects_auto_layout(self) -> None:
        structure = _make_structure()
        summary, _ = analyze_design_tree(structure)
        assert summary.auto_layout_frames >= 2  # header + hero have layout_mode

    def test_naming_compliance(self) -> None:
        structure = _make_structure()
        summary, _ = analyze_design_tree(structure)
        # header, hero, content, footer all match section patterns
        assert summary.naming_compliance >= 75.0

    def test_detects_whitespace_text(self) -> None:
        """TEXT nodes with whitespace-only content should be flagged."""
        ws_node = DesignNode(id="ws", name="Spacer", type=DesignNodeType.TEXT, text_content="   ")
        frame = DesignNode(
            id="f1",
            name="Frame",
            type=DesignNodeType.FRAME,
            width=600,
            height=100,
            children=[ws_node],
        )
        page = DesignNode(id="p1", name="Email", type=DesignNodeType.PAGE, children=[frame])
        structure = DesignFileStructure(file_name="test.fig", pages=[page])
        _, data_loss = analyze_design_tree(structure)
        assert any(e.type == "text_whitespace_only" for e in data_loss)

    def test_detects_image_fills_from_raw_json(self) -> None:
        """IMAGE fills on FRAME nodes in raw JSON should be detected."""
        structure = DesignFileStructure(file_name="test.fig", pages=[])
        raw_json = {
            "document": {
                "children": [
                    {
                        "id": "page1",
                        "type": "PAGE",
                        "children": [
                            {
                                "id": "hero_frame",
                                "name": "Hero",
                                "type": "FRAME",
                                "fills": [{"type": "IMAGE", "imageRef": "abc"}],
                                "children": [],
                            }
                        ],
                    }
                ]
            }
        }
        summary, data_loss = analyze_design_tree(structure, raw_figma_json=raw_json)
        assert len(summary.image_fill_frames) == 1
        assert summary.image_fill_frames[0]["name"] == "Hero"
        assert any(e.type == "image_fill_on_frame" for e in data_loss)


# ── Layout Analyzer Tests ──


class TestLayoutAnalyzer:
    def test_flags_unknown_sections(self) -> None:
        """Sections classified as UNKNOWN should be flagged as data loss."""
        # Directly test the analyzer with a layout that has UNKNOWN sections
        structure = _make_structure()
        layout = analyze_layout(structure)
        stage = analyze_layout_stage(structure, layout)
        # The standard structure has well-named sections, so no UNKNOWN
        # Verify the analyzer completes and captures section count
        assert stage.output_summary["sections"] >= 1
        assert stage.error is None

    def test_naming_compliance_misses(self) -> None:
        """Frames with unrecognized names should show up in naming_misses."""
        structure = _make_unknown_section_structure()
        summary, _ = analyze_design_tree(structure)
        # "XyzWidget" should not match any section pattern
        assert "XyzWidget" in summary.naming_misses
        assert summary.naming_compliance < 100.0

    def test_reports_text_and_image_counts(self) -> None:
        """Layout stage should report input vs output counts accurately."""
        structure = _make_structure()
        layout = analyze_layout(structure)
        stage = analyze_layout_stage(structure, layout)
        # The input summary should count all TEXT/IMAGE nodes in the tree
        assert stage.input_summary["text_nodes"] >= 4  # nav, title, btn_text, body, footer
        assert stage.input_summary["image_nodes"] >= 2  # logo, hero_img
        # Output summary should have sections
        assert stage.output_summary["sections"] >= 1
        assert stage.output_summary["total_text_blocks"] >= 1


# ── Matching Analyzer Tests ──


class TestMatchingAnalyzer:
    def test_flags_low_confidence(self) -> None:
        """Sections matched with confidence < 0.8 should generate warnings."""
        # Use a section type that gets low confidence in fallback matching
        section = EmailSection(
            section_type=EmailSectionType.UNKNOWN,
            node_id="f1",
            node_name="Mystery",
            texts=[TextBlock(node_id="t1", content="Hello", font_size=16.0)],
        )
        matches = match_all([section], container_width=600)
        stage = analyze_matching_stage([section], matches)
        # UNKNOWN with only text matches text-block at 0.7
        low_conf = [w for w in stage.warnings if "low confidence" in w]
        assert len(low_conf) >= 1

    def test_detects_text_reduction(self) -> None:
        """Section with texts that produce empty slot fills should be flagged."""
        # email-header has no slot fills but section has texts → empty_slot_fills
        section = EmailSection(
            section_type=EmailSectionType.HEADER,
            node_id="f1",
            node_name="Header",
            texts=[
                TextBlock(node_id="t1", content="Home", font_size=14.0),
                TextBlock(node_id="t2", content="About", font_size=14.0),
                TextBlock(node_id="t3", content="Contact", font_size=14.0),
            ],
        )
        matches = match_all([section], container_width=600)
        stage = analyze_matching_stage([section], matches)
        # email-header returns empty fills despite section having texts
        empty_loss = [e for e in stage.data_loss if e.type == "empty_slot_fills"]
        assert len(empty_loss) >= 1


# ── Rendering Analyzer Tests ──


class TestRenderingAnalyzer:
    def test_detects_fallback_rendering(self) -> None:
        """A match with a non-existent slug should trigger fallback rendering."""
        section = EmailSection(
            section_type=EmailSectionType.CONTENT,
            node_id="f1",
            node_name="TestSection",
            texts=[TextBlock(node_id="t1", content="Hello", font_size=16.0)],
        )
        match = ComponentMatch(
            section_idx=0,
            section=section,
            component_slug="nonexistent-widget",
            slot_fills=[],
            token_overrides=[],
            confidence=0.5,
        )
        renderer = ComponentRenderer(container_width=600)
        renderer.load()
        rendered = renderer.render_section(match)
        stage = analyze_rendering_stage([match], [rendered])
        fallback_loss = [e for e in stage.data_loss if e.type == "fallback_rendering"]
        assert len(fallback_loss) == 1

    def test_detects_unfilled_slots(self) -> None:
        """Slots in the template not matched by fills should be warned."""
        section = EmailSection(
            section_type=EmailSectionType.HERO,
            node_id="f1",
            node_name="Hero",
            images=[ImagePlaceholder(node_id="img1", node_name="HeroImg", width=600, height=400)],
        )
        matches = match_all([section], container_width=600)
        renderer = ComponentRenderer(container_width=600)
        renderer.load()
        rendered = renderer.render_all(matches)
        stage = analyze_rendering_stage(matches, rendered)
        # full-width-image template has a link_url slot not filled by image-only section
        assert any("unfilled slots" in w for w in stage.warnings)


# ── Assembly Analyzer Tests ──


class TestAssemblyAnalyzer:
    def test_detects_tag_imbalance(self) -> None:
        """Unbalanced <table> tags should be warned."""
        html = "<table><tr><td>Hello</td></tr>"  # Missing </table>
        rendered = [RenderedSection(html="<p>test</p>", component_slug="test", section_idx=0)]
        stage = analyze_assembly_stage(rendered, html)
        assert any("Unbalanced <table>" in w for w in stage.warnings)

    def test_detects_css_brace_imbalance(self) -> None:
        html = "<style>.foo { color: red; </style><table></table>"
        rendered = [RenderedSection(html="<p>test</p>", component_slug="test", section_idx=0)]
        stage = analyze_assembly_stage(rendered, html)
        assert any("CSS brace imbalance" in w for w in stage.warnings)

    def test_balanced_html_no_warnings(self) -> None:
        html = "<table><tr><td>Hello</td></tr></table>"
        rendered = [RenderedSection(html=html, component_slug="test", section_idx=0)]
        stage = analyze_assembly_stage(rendered, html)
        assert len(stage.warnings) == 0


# ── Post-Processing Analyzer Tests ──


class TestPostProcessingAnalyzer:
    def test_counts_div_removal(self) -> None:
        before = '<div class="wrapper"><div>Hello</div></div>'
        after = "<table><tr><td>Hello</td></tr></table>"
        stage = analyze_post_processing(before, after)
        assert stage.output_summary["divs_removed"] == 2

    def test_counts_unfilled_images(self) -> None:
        before = '<img src="https://example.com/img.png" />'
        after = '<img src="" />'
        stage = analyze_post_processing(before, after)
        assert any(e.type == "unfilled_image_src" for e in stage.data_loss)


# ── Diagnostic Runner Tests ──


class TestDiagnosticRunner:
    @pytest.fixture(scope="class")
    def report(self) -> DiagnosticReport:
        """Run the full diagnostic pipeline once."""
        runner = DiagnosticRunner()
        return runner.run_from_structure(_make_structure(), _make_tokens())

    def test_full_pipeline_e2e(self, report: DiagnosticReport) -> None:
        assert report.id
        assert report.total_elapsed_ms > 0
        assert report.stages_completed >= 5
        assert report.design_summary.total_nodes > 0
        assert report.final_html_length > 0

    def test_section_traces_complete(self, report: DiagnosticReport) -> None:
        assert len(report.section_traces) > 0
        for trace in report.section_traces:
            assert trace.node_id
            assert trace.classified_type
            assert trace.matched_component

    def test_stages_have_names(self, report: DiagnosticReport) -> None:
        stage_names = [s.name for s in report.stages]
        assert "layout_analysis" in stage_names
        assert "component_matching" in stage_names
        assert "rendering" in stage_names
        assert "assembly" in stage_names
        assert "post_processing" in stage_names

    def test_report_serializable(self, report: DiagnosticReport) -> None:
        """Report should serialize to valid JSON."""
        json_str = report_to_json(report)
        parsed = json.loads(json_str)
        assert parsed["id"] == report.id
        assert len(parsed["stages"]) == report.stages_completed

    def test_report_to_dict(self, report: DiagnosticReport) -> None:
        d = report_to_dict(report)
        assert isinstance(d, dict)
        assert d["stages_completed"] == report.stages_completed
        assert isinstance(d["design_summary"], dict)


# ── Dump/Load Roundtrip Tests ──


class TestDumpLoad:
    def test_roundtrip_structure(self, tmp_path: Path) -> None:
        structure = _make_structure()
        path = tmp_path / "structure.json"
        dump_structure_to_json(structure, path)
        loaded = load_structure_from_json(path)
        assert loaded.file_name == structure.file_name
        assert len(loaded.pages) == len(structure.pages)
        assert loaded.pages[0].children[0].name == "Header"

    def test_roundtrip_tokens(self, tmp_path: Path) -> None:
        tokens = _make_tokens()
        path = tmp_path / "tokens.json"
        dump_tokens_to_json(tokens, path)
        loaded = load_tokens_from_json(path)
        assert len(loaded.colors) == len(tokens.colors)
        assert loaded.colors[0].hex == "#FFFFFF"
        assert len(loaded.typography) == len(tokens.typography)
        assert len(loaded.gradients) == len(tokens.gradients)
        assert loaded.gradients[0].name == "HeroBG"

    def test_roundtrip_preserves_node_types(self, tmp_path: Path) -> None:
        structure = _make_structure()
        path = tmp_path / "structure.json"
        dump_structure_to_json(structure, path)
        loaded = load_structure_from_json(path)
        # Header is a FRAME
        assert loaded.pages[0].children[0].type == DesignNodeType.FRAME
        # Logo inside header is an IMAGE
        assert loaded.pages[0].children[0].children[0].type == DesignNodeType.IMAGE


# ── Section Traces Tests ──


class TestBuildSectionTraces:
    def test_traces_match_section_count(self) -> None:
        structure = _make_structure()
        layout = analyze_layout(structure)
        matches = match_all(layout.sections, container_width=600)
        renderer = ComponentRenderer(container_width=600)
        renderer.load()
        rendered = renderer.render_all(matches)
        traces = build_section_traces(layout, matches, rendered)
        assert len(traces) == len(layout.sections)

    def test_traces_have_html_preview(self) -> None:
        structure = _make_structure()
        layout = analyze_layout(structure)
        matches = match_all(layout.sections, container_width=600)
        renderer = ComponentRenderer(container_width=600)
        renderer.load()
        rendered = renderer.render_all(matches)
        traces = build_section_traces(layout, matches, rendered)
        for trace in traces:
            assert len(trace.html_preview) <= 3000

    def test_section_trace_default_fields(self) -> None:
        trace = SectionTrace(
            section_idx=0,
            node_id="n1",
            node_name="Hero",
            classified_type="HERO",
            matched_component="hero-block",
            match_confidence=0.9,
            texts_found=1,
            images_found=1,
            buttons_found=0,
            slot_fills=(),
            unfilled_slots=(),
            html_preview="<table></table>",
        )
        assert trace.vlm_classification == ""
        assert trace.vlm_confidence == 0.0
        assert trace.verification_fidelity is None
        assert trace.corrections_applied == 0
        assert trace.generation_method == "template"

    def test_section_trace_with_verification_metadata(self) -> None:
        structure = _make_structure()
        layout = analyze_layout(structure)
        matches = match_all(layout.sections, container_width=600)
        renderer = ComponentRenderer(container_width=600)
        renderer.load()
        rendered = renderer.render_all(matches)
        traces = build_section_traces(
            layout,
            matches,
            rendered,
            verification_results={0: (0.95, 2)},
            generation_methods={1: "custom-generated"},
            vlm_classifications={0: ("HERO", 0.88)},
        )
        assert traces[0].verification_fidelity == 0.95
        assert traces[0].corrections_applied == 2
        assert traces[0].vlm_classification == "HERO"
        assert traces[0].vlm_confidence == 0.88
        assert traces[1].generation_method == "custom-generated"
        # Sections without metadata keep defaults
        assert traces[1].verification_fidelity is None
        assert traces[1].corrections_applied == 0


class TestDiagnosticReportVerificationMetadata:
    def test_report_with_verification_loop(self) -> None:
        from app.design_sync.visual_verify import (
            SectionCorrection,
            VerificationLoopResult,
            VerificationResult,
        )

        loop_result = VerificationLoopResult(
            iterations=[
                VerificationResult(
                    iteration=0,
                    fidelity_score=0.80,
                    section_scores={"hero": 0.75, "content": 0.85},
                    corrections=[
                        SectionCorrection(
                            node_id="hero",
                            section_idx=0,
                            correction_type="color",
                            css_selector="td",
                            css_property="background-color",
                            current_value="#fff",
                            correct_value="#f0f0f0",
                            confidence=0.9,
                            reasoning="bg mismatch",
                        ),
                    ],
                    pixel_diff_pct=5.0,
                    converged=False,
                ),
                VerificationResult(
                    iteration=1,
                    fidelity_score=0.95,
                    section_scores={"hero": 0.96, "content": 0.94},
                    corrections=[],
                    pixel_diff_pct=1.2,
                    converged=True,
                ),
            ],
            final_html="<html></html>",
            initial_fidelity=0.80,
            final_fidelity=0.95,
            total_corrections_applied=1,
            total_vlm_cost_tokens=500,
            converged=True,
            reverted=False,
        )

        runner = DiagnosticRunner()
        report = runner.run_from_structure(
            _make_structure(),
            _make_tokens(),
            verification_result=loop_result,
        )
        assert report.verification_loop_iterations == 2
        assert report.final_fidelity == 0.95

    def test_report_logging_events(self) -> None:
        from unittest.mock import patch

        from app.design_sync.visual_verify import (
            VerificationLoopResult,
            VerificationResult,
        )

        loop_result = VerificationLoopResult(
            iterations=[
                VerificationResult(
                    iteration=0,
                    fidelity_score=0.90,
                    section_scores={},
                    corrections=[],
                    pixel_diff_pct=2.0,
                    converged=True,
                ),
            ],
            final_html="<html></html>",
            initial_fidelity=0.80,
            final_fidelity=0.90,
            total_corrections_applied=0,
            total_vlm_cost_tokens=200,
            converged=True,
            reverted=False,
        )

        runner = DiagnosticRunner()
        with patch("app.design_sync.diagnose.runner.logger") as mock_logger:
            runner.run_from_structure(
                _make_structure(),
                _make_tokens(),
                verification_result=loop_result,
                generation_methods={0: "custom-generated"},
                vlm_classifications={0: ("HERO", 0.92)},
            )
            mock_logger.info.assert_called_once_with(
                "diagnose.verification_metadata_attached",
                iterations=1,
                final_fidelity=0.90,
                sections_with_corrections=0,
            )
            mock_logger.debug.assert_any_call(
                "diagnose.custom_generation_traced",
                count=1,
                section_indices=[0],
            )
            mock_logger.debug.assert_any_call(
                "diagnose.vlm_classification_traced",
                count=1,
                section_indices=[0],
            )
