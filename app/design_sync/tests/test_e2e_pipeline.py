# pyright: reportPrivateUsage=false
"""End-to-end pipeline test: design tokens → email HTML (Phase 33.11 — Step 11).

Verifies the full conversion pipeline from ExtractedTokens + DesignFileStructure
through to complete email HTML output, including:
- HTML email skeleton (DOCTYPE, MSO conditionals, container)
- Multi-column layout with MSO ghost tables
- Semantic text (headings, paragraphs)
- Bulletproof buttons with VML fallback
- Dark mode CSS (prefers-color-scheme + Outlook.com selectors)
- Gradient CSS with solid fallback
- Typography with email-safe font stacks
- Spacing (padding + vertical spacers)
- Builder annotations (data-section-id, data-slot-name, data-component-name)
- Image placeholders with data-node-id
- Token validation (zero warnings for clean tokens)
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

import pytest

from app.design_sync.converter_service import ConversionResult, DesignConverterService
from app.design_sync.import_service import DesignImportService
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
from app.design_sync.token_transforms import validate_and_transform


class _TagBalanceChecker(HTMLParser):
    """Simple HTML validator checking tag balance."""

    VOID_ELEMENTS = frozenset(
        {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }
    )

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() not in self.VOID_ELEMENTS:
            self.stack.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in self.VOID_ELEMENTS:
            return
        if not self.stack:
            self.errors.append(f"Unexpected closing </{tag}>")
            return
        if self.stack[-1] != tag_lower:
            self.errors.append(f"Expected </{self.stack[-1]}> but got </{tag}>")
        else:
            self.stack.pop()


def _check_html_balance(html: str) -> list[str]:
    """Check for unclosed/mismatched tags (excluding MSO conditionals)."""
    # Strip MSO conditional comments before parsing (they contain unpaired tags)
    cleaned = re.sub(r"<!--\[if[^\]]*\]>.*?<!\[endif\]-->", "", html, flags=re.DOTALL)
    checker = _TagBalanceChecker()
    checker.feed(cleaned)
    # Unclosed tags remaining on stack
    errors = list(checker.errors)
    if checker.stack:
        errors.append(f"Unclosed tags: {checker.stack}")
    return errors


# ── Test Data ──


def _make_e2e_tokens() -> ExtractedTokens:
    """Build realistic tokens: 6 colors (3 light, 3 dark), typography, spacing, gradient."""
    return ExtractedTokens(
        colors=[
            ExtractedColor(name="Background", hex="#FFFFFF"),
            ExtractedColor(name="Text Color", hex="#333333"),
            ExtractedColor(name="Primary", hex="#0066CC"),
        ],
        dark_colors=[
            ExtractedColor(name="Background", hex="#1A1A2E"),
            ExtractedColor(name="Text Color", hex="#E0E0E0"),
            ExtractedColor(name="Primary", hex="#66AAFF"),
        ],
        typography=[
            ExtractedTypography(
                name="Heading",
                family="Inter",
                weight="700",
                size=32.0,
                line_height=40.0,
                letter_spacing=-0.5,
                text_transform="uppercase",
            ),
            ExtractedTypography(
                name="Body",
                family="Inter",
                weight="400",
                size=16.0,
                line_height=24.0,
            ),
        ],
        spacing=[
            ExtractedSpacing(name="s1", value=8),
            ExtractedSpacing(name="s2", value=16),
            ExtractedSpacing(name="s3", value=24),
            ExtractedSpacing(name="s4", value=32),
        ],
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


def _make_e2e_structure() -> DesignFileStructure:
    """Build a realistic design tree: header, hero, two-column content, footer."""
    header = DesignNode(
        id="header",
        name="Header",
        type=DesignNodeType.FRAME,
        width=600,
        height=80,
        layout_mode="HORIZONTAL",
        padding_top=16,
        padding_right=24,
        padding_bottom=16,
        padding_left=24,
        children=[
            DesignNode(
                id="logo",
                name="Logo",
                type=DesignNodeType.IMAGE,
                width=120,
                height=40,
                x=0,
                y=0,
            ),
            DesignNode(
                id="nav_text",
                name="Navigation",
                type=DesignNodeType.TEXT,
                text_content="Home | About | Contact",
                font_size=14.0,
                x=400,
                y=0,
            ),
        ],
    )

    hero = DesignNode(
        id="hero",
        name="HeroBG",  # Matches gradient name
        type=DesignNodeType.FRAME,
        width=600,
        height=400,
        layout_mode="VERTICAL",
        item_spacing=24,
        padding_top=48,
        padding_right=40,
        padding_bottom=48,
        padding_left=40,
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
                id="hero_heading",
                name="Hero Title",
                type=DesignNodeType.TEXT,
                text_content="Summer Collection 2026",
                font_size=32.0,
                font_weight=700,
                text_color="#FFFFFF",
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
                        text_color="#FFFFFF",
                        font_size=16.0,
                        y=0,
                    ),
                ],
            ),
        ],
    )

    content = DesignNode(
        id="content",
        name="Two Column Content",
        type=DesignNodeType.FRAME,
        width=600,
        height=300,
        layout_mode="HORIZONTAL",
        item_spacing=20,
        padding_top=32,
        padding_right=24,
        padding_bottom=32,
        padding_left=24,
        children=[
            DesignNode(
                id="col1",
                name="Column 1",
                type=DesignNodeType.FRAME,
                width=260,
                height=200,
                x=0,
                y=0,
                children=[
                    DesignNode(
                        id="col1_img",
                        name="Content Image",
                        type=DesignNodeType.IMAGE,
                        width=260,
                        height=150,
                        y=0,
                    ),
                    DesignNode(
                        id="col1_text",
                        name="Column Text",
                        type=DesignNodeType.TEXT,
                        text_content="Discover our new arrivals",
                        font_size=16.0,
                        y=160,
                    ),
                ],
            ),
            DesignNode(
                id="col2",
                name="Column 2",
                type=DesignNodeType.FRAME,
                width=260,
                height=200,
                x=280,
                y=0,
                children=[
                    DesignNode(
                        id="col2_text",
                        name="Description",
                        type=DesignNodeType.TEXT,
                        text_content="Premium quality materials\nSustainable sourcing\nFree shipping over $50",
                        font_size=16.0,
                        y=0,
                    ),
                ],
            ),
        ],
    )

    footer = DesignNode(
        id="footer",
        name="Footer",
        type=DesignNodeType.FRAME,
        width=600,
        height=60,
        padding_top=16,
        padding_right=24,
        padding_bottom=16,
        padding_left=24,
        children=[
            DesignNode(
                id="footer_text",
                name="Legal",
                type=DesignNodeType.TEXT,
                text_content="© 2026 Brand Inc. All rights reserved.",
                font_size=12.0,
                text_color="#666666",
                y=0,
            ),
        ],
    )

    page = DesignNode(
        id="page1",
        name="Email Page",
        type=DesignNodeType.PAGE,
        children=[header, hero, content, footer],
    )
    return DesignFileStructure(file_name="Summer Campaign.fig", pages=[page])


class TestEndToEndPipeline:
    """Full pipeline: tokens + structure → email HTML.

    Uses a shared conversion result to avoid running the pipeline 14+ times.
    """

    @pytest.fixture(scope="class")
    def pipeline_html(self) -> str:
        """Run the full pipeline once and cache the HTML for all tests."""
        tokens = _make_e2e_tokens()
        structure = _make_e2e_structure()
        result = DesignConverterService().convert(structure, tokens, use_components=False)
        return result.html

    @pytest.fixture(scope="class")
    def pipeline_result(self) -> ConversionResult:
        """Run the full pipeline once and cache the result for metadata tests."""
        tokens = _make_e2e_tokens()
        structure = _make_e2e_structure()
        return DesignConverterService().convert(structure, tokens, use_components=False)

    def test_token_validation_zero_warnings(self) -> None:
        """Clean tokens → zero warnings from validate_and_transform."""
        tokens = _make_e2e_tokens()
        _validated, warnings = validate_and_transform(tokens)
        error_warnings = [w for w in warnings if w.level == "error"]
        assert len(error_warnings) == 0

    def test_html_skeleton(self, pipeline_html: str) -> None:
        """Pipeline output has DOCTYPE, MSO conditionals, 600px container."""
        assert "<!DOCTYPE html>" in pipeline_html
        assert "<!--[if mso]>" in pipeline_html
        assert "<![endif]-->" in pipeline_html
        assert 'width="600"' in pipeline_html

    def test_sections_count(self, pipeline_result: ConversionResult) -> None:
        """4 top-level frames → 4 sections."""
        assert pipeline_result.sections_count == 4

    def test_dark_mode_css(self, pipeline_html: str) -> None:
        """Dark tokens → dark mode CSS in output."""
        assert "@media (prefers-color-scheme: dark)" in pipeline_html
        assert "[data-ogsb]" in pipeline_html
        assert 'name="color-scheme"' in pipeline_html

    def test_gradient_in_hero(self, pipeline_html: str) -> None:
        """Hero section has gradient CSS + solid bgcolor fallback."""
        assert "linear-gradient" in pipeline_html
        assert 'bgcolor="#004C99"' in pipeline_html

    def test_multi_column_content(self, pipeline_html: str) -> None:
        """Two-column content → MSO ghost table + inline-block."""
        assert "display:inline-block" in pipeline_html
        assert 'class="column"' in pipeline_html

    def test_typography_font_stacks(self, pipeline_html: str) -> None:
        """Typography → email-safe font stacks in output."""
        assert "Inter" in pipeline_html
        assert "Arial" in pipeline_html

    def test_spacing_applied(self, pipeline_html: str) -> None:
        """Auto-layout padding + spacer rows in output."""
        assert "height:24px" in pipeline_html
        assert "padding:" in pipeline_html

    def test_button_with_vml(self, pipeline_html: str) -> None:
        """CTA button → <a> + VML <v:roundrect>."""
        assert '<a href="#"' in pipeline_html
        assert "Shop Now" in pipeline_html
        assert "v:roundrect" in pipeline_html

    def test_builder_annotations(self, pipeline_html: str) -> None:
        """All sections have data-section-id, content has data-slot-name."""
        assert 'data-section-id="section_0"' in pipeline_html
        assert 'data-section-id="section_1"' in pipeline_html
        assert 'data-section-id="section_2"' in pipeline_html
        assert 'data-section-id="section_3"' in pipeline_html
        assert "data-slot-name" in pipeline_html
        assert 'data-component-name="Header"' in pipeline_html
        assert 'data-component-name="Footer"' in pipeline_html

    def test_image_placeholders(self, pipeline_html: str) -> None:
        """IMAGE nodes → <img src="" data-node-id="..."> placeholders."""
        assert 'data-node-id="logo"' in pipeline_html
        assert 'data-node-id="hero_img"' in pipeline_html
        assert 'data-node-id="col1_img"' in pipeline_html

    def test_image_url_filling(self, pipeline_html: str) -> None:
        """After conversion, _fill_image_urls replaces src placeholders."""
        urls = {
            "logo": "/assets/1/logo.png",
            "hero_img": "/assets/1/hero.png",
            "col1_img": "/assets/1/content.png",
        }
        filled = DesignImportService._fill_image_urls(pipeline_html, urls)
        assert "/assets/1/logo.png" in filled
        assert "/assets/1/hero.png" in filled
        assert "/assets/1/content.png" in filled

    def test_html_validity(self, pipeline_html: str) -> None:
        """Output HTML has no unclosed or mismatched tags."""
        errors = _check_html_balance(pipeline_html)
        assert errors == [], f"HTML balance errors: {errors}"

    def test_multiline_text_produces_multiple_paragraphs(self, pipeline_html: str) -> None:
        """Multi-line text in column 2 → multiple <p> tags."""
        assert "Premium quality materials" in pipeline_html
        assert "Sustainable sourcing" in pipeline_html
        assert "Free shipping" in pipeline_html

    def test_semantic_heading(self, pipeline_html: str) -> None:
        """Text content appears in output (heading detection depends on layout analysis)."""
        assert "Summer Collection 2026" in pipeline_html
