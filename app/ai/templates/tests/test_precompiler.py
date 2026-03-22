# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Tests for TemplatePrecompiler."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest

from app.ai.templates.models import GoldenTemplate, TemplateMetadata
from app.ai.templates.precompiler import (
    CSS_PREOPTIMIZED_MARKER,
    TemplatePrecompiler,
)


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
    from app.email_engine.tests.test_css_compiler import _mock_registry

    reg = _mock_registry(support_none=False)
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
