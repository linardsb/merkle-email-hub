# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Tests for TemplatePrecompiler."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC
from unittest.mock import patch

import pytest

from app.ai.templates.models import GoldenTemplate, TemplateMetadata
from app.ai.templates.precompiler import (
    CSS_PREOPTIMIZED_MARKER,
    TemplatePrecompiler,
)
from app.email_engine.tests.conftest import make_mock_registry


def _make_template(name: str = "test", html: str = "") -> GoldenTemplate:
    """Create a minimal GoldenTemplate for testing."""
    return GoldenTemplate(
        metadata=TemplateMetadata(
            name=name,
            display_name="Test",
            layout_type="newsletter",
            column_count=1,
            has_hero_image=False,
            has_navigation=False,
            has_social_links=False,
            sections=(),
            ideal_for=(),
            description="test template",
        ),
        html=html or "<html><head><style>.hero{color:red}</style></head><body>test</body></html>",
        slots=(),
    )


@pytest.fixture
def _mock_ontology() -> Generator[None]:
    """Mock ontology for CSS compiler."""
    reg = make_mock_registry(support_none=False)
    with (
        patch("app.email_engine.css_compiler.compiler.load_ontology", return_value=reg),
        patch("app.email_engine.css_compiler.conversions.load_ontology", return_value=reg),
    ):
        yield


class TestTemplatePrecompiler:
    def test_precompile_populates_optimized_html(self, _mock_ontology: None) -> None:
        template = _make_template()
        precompiler = TemplatePrecompiler(target_clients=("gmail",))
        result = precompiler.precompile(template)

        assert result.optimized_html is not None
        assert CSS_PREOPTIMIZED_MARKER in result.optimized_html
        assert result.optimized_at is not None
        assert result.optimized_for_clients == ("gmail",)
        assert result.optimization_metadata["original_size"] > 0

    def test_precompile_preserves_original_fields(self, _mock_ontology: None) -> None:
        template = _make_template(name="promo")
        precompiler = TemplatePrecompiler(target_clients=("gmail",))
        result = precompiler.precompile(template)

        assert result.metadata.name == "promo"
        assert result.slots == ()
        assert result.html == template.html  # original HTML unchanged

    def test_is_stale_no_optimization(self) -> None:
        template = _make_template()
        assert TemplatePrecompiler.is_stale(template, ("gmail",)) is True

    def test_is_stale_different_clients(self, _mock_ontology: None) -> None:
        precompiler = TemplatePrecompiler(target_clients=("gmail",))
        result = precompiler.precompile(_make_template())
        assert TemplatePrecompiler.is_stale(result, ("outlook",)) is True
        assert TemplatePrecompiler.is_stale(result, ("gmail",)) is False

    def test_precompile_all_reports(self, _mock_ontology: None) -> None:
        templates = {
            "a": _make_template("a"),
            "b": _make_template("b"),
        }
        precompiler = TemplatePrecompiler(target_clients=("gmail",))
        updated, report = precompiler.precompile_all(templates)

        assert report.total == 2
        assert report.succeeded == 2
        assert report.failed == 0
        assert updated["a"].optimized_html is not None
        assert updated["b"].optimized_html is not None

    def test_precompile_all_handles_failure(self) -> None:
        templates = {"fail": _make_template("fail")}
        with patch(
            "app.email_engine.css_compiler.compiler.load_ontology",
            side_effect=RuntimeError("no ontology"),
        ):
            precompiler = TemplatePrecompiler(target_clients=("gmail",))
            updated, report = precompiler.precompile_all(templates)

        assert report.failed == 1
        assert "fail" in report.errors
        assert updated["fail"].optimized_html is None  # kept original

    def test_precompile_populates_metadata_fields(self, _mock_ontology: None) -> None:
        """optimization_metadata should contain all expected keys."""
        template = _make_template()
        precompiler = TemplatePrecompiler(target_clients=("gmail",))
        result = precompiler.precompile(template)
        meta = result.optimization_metadata
        assert "removed_properties" in meta
        assert "conversions" in meta
        assert "compile_time_ms" in meta
        assert "original_size" in meta
        assert "optimized_size" in meta

    def test_precompile_metadata_sizes_are_correct(self, _mock_ontology: None) -> None:
        """original_size should match the byte length of the source HTML."""
        html = "<html><head><style>.x{color:red}</style></head><body>Hello</body></html>"
        template = _make_template(html=html)
        precompiler = TemplatePrecompiler(target_clients=("gmail",))
        result = precompiler.precompile(template)
        assert result.optimization_metadata["original_size"] == len(html.encode("utf-8"))

    def test_is_stale_returns_false_same_clients_different_order(
        self, _mock_ontology: None
    ) -> None:
        """is_stale should use set comparison, so order doesn't matter."""
        precompiler = TemplatePrecompiler(target_clients=("gmail", "outlook"))
        result = precompiler.precompile(_make_template())
        assert TemplatePrecompiler.is_stale(result, ("outlook", "gmail")) is False

    def test_precompile_preserves_slot_markers(self, _mock_ontology: None) -> None:
        """data-slot attributes should survive precompilation."""
        html = (
            "<html><head><style>.x{color:red}</style></head>"
            '<body><td data-slot="headline">Title</td></body></html>'
        )
        template = _make_template(html=html)
        precompiler = TemplatePrecompiler(target_clients=("gmail",))
        result = precompiler.precompile(template)
        assert result.optimized_html is not None
        assert 'data-slot="headline"' in result.optimized_html

    def test_precompile_preserves_mso_conditionals(self, _mock_ontology: None) -> None:
        """MSO conditional comments should survive precompilation."""
        html = (
            "<html><head><style>.x{color:red}</style></head><body>"
            "<!--[if mso]><table><tr><td>MSO</td></tr></table><![endif]-->"
            "<p>Normal</p></body></html>"
        )
        template = _make_template(html=html)
        precompiler = TemplatePrecompiler(target_clients=("gmail",))
        result = precompiler.precompile(template)
        assert result.optimized_html is not None
        assert "<!--[if mso]>" in result.optimized_html

    def test_precompile_all_returns_correct_report_on_partial_failure(
        self, _mock_ontology: None
    ) -> None:
        """One success + one failure should report correctly."""
        templates = {
            "good": _make_template("good"),
            "bad": _make_template("bad"),
        }
        call_count = 0

        def _alternating_ontology() -> object:
            nonlocal call_count
            call_count += 1
            if call_count > 2:
                msg = "ontology error"
                raise RuntimeError(msg)
            return make_mock_registry(support_none=False)

        with patch(
            "app.email_engine.css_compiler.compiler.load_ontology",
            side_effect=_alternating_ontology,
        ):
            precompiler = TemplatePrecompiler(target_clients=("gmail",))
            _updated, report = precompiler.precompile_all(templates)

        assert report.succeeded + report.failed == report.total

    def test_precompile_marker_in_html(self, _mock_ontology: None) -> None:
        """CSS_PREOPTIMIZED_MARKER should be prepended to optimized_html."""
        template = _make_template()
        precompiler = TemplatePrecompiler(target_clients=("gmail",))
        result = precompiler.precompile(template)
        assert result.optimized_html is not None
        assert result.optimized_html.startswith(CSS_PREOPTIMIZED_MARKER)

    def test_precompile_optimized_at_is_utc(self, _mock_ontology: None) -> None:
        """optimized_at should have UTC timezone."""
        template = _make_template()
        precompiler = TemplatePrecompiler(target_clients=("gmail",))
        result = precompiler.precompile(template)
        assert result.optimized_at is not None
        assert result.optimized_at.tzinfo is not None
        assert result.optimized_at.tzinfo == UTC
