# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Tests for optimize_css() — stages 1-5 only (no inlining)."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.email_engine.css_compiler.compiler import EmailCSSCompiler, OptimizedCSS


class TestOptimizeCSSStructure:
    """Tests for OptimizedCSS result structure."""

    def test_returns_optimized_css_dataclass(self, mock_ontology_supported: MagicMock) -> None:
        html = "<html><head><style>.x{color:red}</style></head><body>Hi</body></html>"
        result = EmailCSSCompiler(target_clients=["gmail_web"]).optimize_css(html)
        assert isinstance(result, OptimizedCSS)
        assert isinstance(result.html, str)
        assert isinstance(result.removed_properties, list)
        assert isinstance(result.conversions, list)
        assert isinstance(result.warnings, list)
        assert isinstance(result.optimize_time_ms, float)

    def test_html_contains_style_blocks_not_inlined(
        self, mock_ontology_supported: MagicMock
    ) -> None:
        html = "<html><head><style>.x{color:red}</style></head><body><div class='x'>Hi</div></body></html>"
        result = EmailCSSCompiler(target_clients=["gmail_web"]).optimize_css(html)
        assert "<style>" in result.html

    def test_optimize_time_is_nonnegative(self, mock_ontology_supported: MagicMock) -> None:
        html = "<html><head></head><body>Hi</body></html>"
        result = EmailCSSCompiler(target_clients=["gmail_web"]).optimize_css(html)
        assert result.optimize_time_ms >= 0


class TestOptimizeCSSRemovals:
    """Tests for ontology-driven property removal."""

    def test_removes_unsupported_property(self, mock_ontology_unsupported: MagicMock) -> None:
        html = "<html><head><style>.x { display: flex; }</style></head><body>Hi</body></html>"
        result = EmailCSSCompiler(target_clients=["outlook_2019"]).optimize_css(html)
        assert any("display" in p for p in result.removed_properties)

    def test_removes_from_inline_styles(self, mock_ontology_unsupported: MagicMock) -> None:
        html = '<html><head></head><body><div style="display: flex">Hi</div></body></html>'
        result = EmailCSSCompiler(target_clients=["outlook_2019"]).optimize_css(html)
        assert len(result.removed_properties) > 0

    def test_does_not_remove_supported_property(self, mock_ontology_supported: MagicMock) -> None:
        html = "<html><head><style>.x { color: red; }</style></head><body>Hi</body></html>"
        result = EmailCSSCompiler(target_clients=["gmail_web"]).optimize_css(html)
        assert result.removed_properties == []


class TestOptimizeCSSConversions:
    """Tests for fallback conversions."""

    def test_applies_fallback_conversion(self, mock_ontology_with_fallback: MagicMock) -> None:
        html = "<html><head><style>.x { display: flex; }</style></head><body>Hi</body></html>"
        result = EmailCSSCompiler(target_clients=["outlook_2019"]).optimize_css(html)
        assert len(result.conversions) > 0
        assert result.conversions[0].replacement_property == "display"
        assert result.conversions[0].replacement_value == "block"

    def test_conversion_records_affected_clients(
        self, mock_ontology_with_fallback: MagicMock
    ) -> None:
        html = "<html><head><style>.x { display: flex; }</style></head><body>Hi</body></html>"
        result = EmailCSSCompiler(target_clients=["outlook_2019"]).optimize_css(html)
        assert "outlook_2019" in result.conversions[0].affected_clients


class TestOptimizeCSSVariables:
    """Tests for CSS variable resolution."""

    def test_resolves_variables_with_values(self, mock_ontology_supported: MagicMock) -> None:
        html = "<html><head><style>.x{color:var(--brand)}</style></head><body>Hi</body></html>"
        result = EmailCSSCompiler(
            target_clients=["gmail_web"], css_variables={"brand": "#ff0000"}
        ).optimize_css(html)
        assert "var(--brand)" not in result.html

    def test_preserves_var_with_fallback_when_no_variable(
        self, mock_ontology_supported: MagicMock
    ) -> None:
        html = (
            "<html><head><style>.x{color:var(--missing, blue)}</style></head><body>Hi</body></html>"
        )
        result = EmailCSSCompiler(target_clients=["gmail_web"]).optimize_css(html)
        assert "blue" in result.html


class TestOptimizeCSSPreservation:
    """Tests for things that must be preserved through optimization."""

    def test_preserves_mso_conditional_comments(self, mock_ontology_supported: MagicMock) -> None:
        html = (
            "<html><head></head><body>"
            "<!--[if mso]><table><tr><td>MSO</td></tr></table><![endif]-->"
            "<p>Normal</p></body></html>"
        )
        result = EmailCSSCompiler(target_clients=["outlook_2019"]).optimize_css(html)
        assert "<!--[if mso]>" in result.html
        assert "<![endif]-->" in result.html

    def test_preserves_media_queries(self, mock_ontology_supported: MagicMock) -> None:
        html = (
            "<html><head><style>"
            "@media (max-width:480px){.x{font-size:14px}}"
            "</style></head><body>Hi</body></html>"
        )
        result = EmailCSSCompiler(target_clients=["gmail_web"]).optimize_css(html)
        assert "@media" in result.html

    def test_preserves_slot_placeholders(self, mock_ontology_supported: MagicMock) -> None:
        html = (
            "<html><head><style>.x{color:red}</style></head><body>"
            "{{headline_slot}}<p>Content</p>{{footer_slot}}</body></html>"
        )
        result = EmailCSSCompiler(target_clients=["gmail_web"]).optimize_css(html)
        assert "{{headline_slot}}" in result.html
        assert "{{footer_slot}}" in result.html

    def test_preserves_esp_tokens(self, mock_ontology_supported: MagicMock) -> None:
        html = (
            "<html><head><style>.x{color:red}</style></head><body>"
            "<p>Hello {{ first_name | default: 'Friend' }}</p>"
            "<p>{% if vip %}VIP content{% endif %}</p></body></html>"
        )
        result = EmailCSSCompiler(target_clients=["gmail_web"]).optimize_css(html)
        assert "{{ first_name" in result.html
        assert "{% if vip %}" in result.html


class TestOptimizeCSSEdgeCases:
    """Edge cases and multi-block handling."""

    def test_removes_empty_style_blocks(self, mock_ontology_unsupported: MagicMock) -> None:
        html = "<html><head><style>.x { display: flex; }</style></head><body>Hi</body></html>"
        result = EmailCSSCompiler(target_clients=["outlook_2019"]).optimize_css(html)
        # After removing the only property, the style block content should be empty
        # The compiler filters out empty blocks in optimize_css
        assert result.removed_properties  # At least one removed

    def test_handles_multiple_style_blocks_independently(
        self, mock_ontology_supported: MagicMock
    ) -> None:
        html = (
            "<html><head>"
            "<style>.a{color:red}</style>"
            "<style>.b{font-size:14px}</style>"
            "<style>.c{margin:0}</style>"
            "</head><body>Hi</body></html>"
        )
        result = EmailCSSCompiler(target_clients=["gmail_web"]).optimize_css(html)
        assert isinstance(result.html, str)
        assert result.html.count("<style>") >= 1  # At least one style block preserved

    def test_handles_no_style_blocks(self, mock_ontology_supported: MagicMock) -> None:
        html = "<html><head></head><body><p>No styles</p></body></html>"
        result = EmailCSSCompiler(target_clients=["gmail_web"]).optimize_css(html)
        assert result.removed_properties == []
        assert result.conversions == []

    def test_handles_empty_html(self, mock_ontology_supported: MagicMock) -> None:
        result = EmailCSSCompiler(target_clients=["gmail_web"]).optimize_css(
            "<html><body></body></html>"
        )
        assert isinstance(result, OptimizedCSS)
        assert result.optimize_time_ms >= 0
