# pyright: reportPrivateUsage=false
"""Tests for dark mode CSS generation and gradient rendering in email output (Phase 33.11 — Step 8)."""

from __future__ import annotations

from app.design_sync.converter import _gradient_to_css, node_to_email_html
from app.design_sync.converter_service import (
    DesignConverterService,
    dark_mode_meta_tags,
    dark_mode_style_block,
)
from app.design_sync.protocol import (
    DesignFileStructure,
    DesignNode,
    DesignNodeType,
    ExtractedColor,
    ExtractedGradient,
    ExtractedTokens,
)
from app.design_sync.render_context import RenderContext


class TestDarkModeCSSGeneration:
    """Integration tests for dark mode CSS in full pipeline output."""

    def _make_dark_tokens(self) -> ExtractedTokens:
        return ExtractedTokens(
            colors=[
                ExtractedColor(name="Background", hex="#FFFFFF"),
                ExtractedColor(name="Text Color", hex="#000000"),
            ],
            dark_colors=[
                ExtractedColor(name="Background", hex="#1A1A2E"),
                ExtractedColor(name="Text Color", hex="#E0E0E0"),
            ],
        )

    def test_prefers_color_scheme_in_output(self) -> None:
        """Dark tokens → @media (prefers-color-scheme: dark) in pipeline output."""
        tokens = self._make_dark_tokens()
        structure = DesignFileStructure(
            file_name="test",
            pages=[
                DesignNode(
                    id="page1",
                    name="Page",
                    type=DesignNodeType.PAGE,
                    children=[
                        DesignNode(
                            id="f1",
                            name="Frame",
                            type=DesignNodeType.FRAME,
                            width=600,
                            height=200,
                            children=[
                                DesignNode(
                                    id="t1",
                                    name="T",
                                    type=DesignNodeType.TEXT,
                                    text_content="X",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        result = DesignConverterService().convert(structure, tokens, use_components=False)
        assert "@media (prefers-color-scheme: dark)" in result.html

    def test_ogsc_selectors_in_output(self) -> None:
        """Dark tokens → Outlook.com [data-ogsc]/[data-ogsb] selectors."""
        tokens = self._make_dark_tokens()
        css = dark_mode_style_block(tokens.colors, tokens.dark_colors)
        assert "[data-ogsc]" in css
        assert "[data-ogsb]" in css

    def test_no_dark_no_css_block(self) -> None:
        """No dark tokens → empty dark CSS block."""
        css = dark_mode_style_block(
            [ExtractedColor(name="bg", hex="#FFFFFF")],
            [],
        )
        assert css == ""

    def test_no_dark_no_meta_tags(self) -> None:
        """No dark tokens → no color-scheme meta in pipeline output."""
        tokens = ExtractedTokens(colors=[ExtractedColor(name="bg", hex="#FFFFFF")])
        structure = DesignFileStructure(
            file_name="test",
            pages=[
                DesignNode(
                    id="page1",
                    name="Page",
                    type=DesignNodeType.PAGE,
                    children=[
                        DesignNode(
                            id="f1",
                            name="Frame",
                            type=DesignNodeType.FRAME,
                            width=600,
                            height=200,
                            children=[
                                DesignNode(
                                    id="t1",
                                    name="T",
                                    type=DesignNodeType.TEXT,
                                    text_content="X",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        result = DesignConverterService().convert(structure, tokens, use_components=False)
        assert 'name="color-scheme"' not in result.html

    def test_meta_tags_present_with_dark(self) -> None:
        """Dark tokens → color-scheme + supported-color-schemes meta."""
        meta = dark_mode_meta_tags()
        assert 'name="color-scheme"' in meta
        assert 'name="supported-color-schemes"' in meta
        assert "light dark" in meta


class TestGradientRendering:
    """Tests for gradient CSS output in email HTML."""

    def test_linear_gradient_css(self) -> None:
        """Linear gradient → background: linear-gradient(...)."""
        grad = ExtractedGradient(
            name="hero-bg",
            type="linear",
            angle=180.0,
            stops=(("#FF0000", 0.0), ("#0000FF", 1.0)),
            fallback_hex="#800080",
        )
        css = _gradient_to_css(grad)
        assert "linear-gradient(180.0deg" in css
        assert "#FF0000" in css
        assert "#0000FF" in css

    def test_3stop_gradient(self) -> None:
        """Gradient with 3 stops → all 3 in CSS output."""
        grad = ExtractedGradient(
            name="rainbow",
            type="linear",
            angle=90.0,
            stops=(("#FF0000", 0.0), ("#00FF00", 0.5), ("#0000FF", 1.0)),
            fallback_hex="#808080",
        )
        css = _gradient_to_css(grad)
        assert "90.0deg" in css
        assert "#FF0000" in css
        assert "#00FF00" in css
        assert "#0000FF" in css
        assert "50.0%" in css

    def test_gradient_on_frame_with_bgcolor_fallback(self) -> None:
        """Frame with gradient → CSS background + bgcolor fallback for Outlook."""
        grad = ExtractedGradient(
            name="HeroBG",
            type="linear",
            angle=180.0,
            stops=(("#FF0000", 0.0), ("#0000FF", 1.0)),
            fallback_hex="#800080",
        )
        frame = DesignNode(
            id="frame1",
            name="HeroBG",
            type=DesignNodeType.FRAME,
            width=600,
            height=300,
            children=[
                DesignNode(
                    id="txt1", name="Title", type=DesignNodeType.TEXT, text_content="Hello", y=0
                ),
            ],
        )
        html = node_to_email_html(
            frame, RenderContext.from_legacy_kwargs(gradients_map={"HeroBG": grad})
        )
        assert "linear-gradient" in html
        assert 'bgcolor="#800080"' in html
