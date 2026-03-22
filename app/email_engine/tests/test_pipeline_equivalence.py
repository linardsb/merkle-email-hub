# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Pipeline equivalence regression tests.

For each golden template from the template library, build via:
1. Old path: EmailCSSCompiler.compile() (stages 1-7)
2. New path: EmailCSSCompiler.optimize_css() (stages 1-5 only)

Verify the optimization stages produce consistent results — same properties
removed, same conversions applied, same structural elements preserved.
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest

from app.email_engine.css_compiler.compiler import EmailCSSCompiler
from app.email_engine.tests.conftest import make_mock_registry


@pytest.fixture(autouse=True)
def _mock_ontology() -> Generator[None]:
    """Use consistent mock ontology for equivalence tests."""
    reg = make_mock_registry(support_none=False)
    with (
        patch("app.email_engine.css_compiler.compiler.load_ontology", return_value=reg),
        patch("app.email_engine.css_compiler.conversions.load_ontology", return_value=reg),
    ):
        yield


class TestPipelineEquivalence:
    """Verify compile() and optimize_css() produce consistent optimization results
    across real golden templates."""

    def test_optimization_stages_match(self, representative_templates: dict[str, str]) -> None:
        """Stages 1-5 produce same removed/converted properties in both paths."""
        for name, html in representative_templates.items():
            compiler = EmailCSSCompiler(target_clients=["gmail_web", "outlook_2019"])
            compile_result = compiler.compile(html)
            optimize_result = compiler.optimize_css(html)

            assert set(compile_result.removed_properties) == set(
                optimize_result.removed_properties
            ), f"Template '{name}': removed properties differ"
            compile_convs = {
                (c.original_property, c.replacement_property) for c in compile_result.conversions
            }
            optimize_convs = {
                (c.original_property, c.replacement_property) for c in optimize_result.conversions
            }
            assert compile_convs == optimize_convs, f"Template '{name}': conversions differ"

    def test_mso_conditionals_preserved_both_paths(
        self, representative_templates: dict[str, str]
    ) -> None:
        """MSO conditionals survive both compile and optimize paths."""
        for name, html in representative_templates.items():
            compiler = EmailCSSCompiler(target_clients=["outlook_2019"])
            compile_result = compiler.compile(html)
            optimize_result = compiler.optimize_css(html)

            if "<!--[if mso]>" in html:
                assert "<!--[if mso]>" in compile_result.html, (
                    f"Template '{name}': MSO lost in compile"
                )
                assert "<!--[if mso]>" in optimize_result.html, (
                    f"Template '{name}': MSO lost in optimize"
                )

    def test_media_queries_preserved_both_paths(
        self, representative_templates: dict[str, str]
    ) -> None:
        """@media rules survive both paths."""
        for name, html in representative_templates.items():
            compiler = EmailCSSCompiler(target_clients=["gmail_web"])
            compile_result = compiler.compile(html)
            optimize_result = compiler.optimize_css(html)

            if "@media" in html:
                assert "@media" in compile_result.html, f"Template '{name}': @media lost in compile"
                assert "@media" in optimize_result.html, (
                    f"Template '{name}': @media lost in optimize"
                )

    def test_no_regressions_in_compiled_output(
        self, representative_templates: dict[str, str]
    ) -> None:
        """Compiled output is valid HTML with body content preserved."""
        for name, html in representative_templates.items():
            compiler = EmailCSSCompiler(target_clients=["gmail_web"])
            result = compiler.compile(html)
            assert "<body" in result.html.lower(), f"Template '{name}': missing <body>"
            assert result.compiled_size > 0
            assert result.compiled_size <= result.original_size * 1.5, (
                f"Template '{name}': output grew unexpectedly"
            )

    def test_all_15_templates_compile_without_error(self, golden_templates: dict[str, str]) -> None:
        """Every golden template in the library compiles successfully."""
        compiler = EmailCSSCompiler(target_clients=["gmail_web", "outlook_2019"])
        for name, html in golden_templates.items():
            result = compiler.compile(html)
            assert result.compiled_size > 0, f"Template '{name}': zero compiled size"

    def test_all_15_templates_optimize_without_error(
        self, golden_templates: dict[str, str]
    ) -> None:
        """Every golden template in the library optimizes successfully."""
        compiler = EmailCSSCompiler(target_clients=["gmail_web", "outlook_2019"])
        for name, html in golden_templates.items():
            result = compiler.optimize_css(html)
            assert isinstance(result.html, str), f"Template '{name}': optimize failed"

    def test_all_components_compile_without_error(self, component_html: dict[str, str]) -> None:
        """Every seeded component HTML compiles successfully."""
        compiler = EmailCSSCompiler(target_clients=["gmail_web", "outlook_2019"])
        for slug, html in component_html.items():
            result = compiler.compile(html)
            assert result.compiled_size > 0, f"Component '{slug}': zero compiled size"

    def test_all_components_optimize_without_error(self, component_html: dict[str, str]) -> None:
        """Every seeded component HTML optimizes successfully."""
        compiler = EmailCSSCompiler(target_clients=["gmail_web", "outlook_2019"])
        for slug, html in component_html.items():
            result = compiler.optimize_css(html)
            assert isinstance(result.html, str), f"Component '{slug}': optimize failed"

    def test_email_shell_preserves_mso_and_dark_mode(self, component_html: dict[str, str]) -> None:
        """Email shell component preserves MSO conditionals and dark mode CSS."""
        shell = component_html.get("email-shell", "")
        if not shell:
            pytest.skip("email-shell component not in seeds")
        compiler = EmailCSSCompiler(target_clients=["gmail_web", "outlook_2019"])

        compile_result = compiler.compile(shell)
        optimize_result = compiler.optimize_css(shell)

        for result, label in [(compile_result.html, "compile"), (optimize_result.html, "optimize")]:
            assert "<!--[if mso]>" in result, f"email-shell {label}: MSO conditionals lost"
            assert "prefers-color-scheme" in result, f"email-shell {label}: dark mode CSS lost"

    def test_component_slot_markers_preserved_in_optimize(
        self, representative_components: dict[str, str]
    ) -> None:
        """Component slot markers (data-slot) survive the optimize_css() path."""
        compiler = EmailCSSCompiler(target_clients=["gmail_web"])
        for slug, html in representative_components.items():
            if "data-slot" not in html:
                continue
            optimize_result = compiler.optimize_css(html)
            assert "data-slot" in optimize_result.html, (
                f"Component '{slug}': slots lost in optimize"
            )
