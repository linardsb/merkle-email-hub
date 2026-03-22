"""Tests for the CSS audit QA check."""

from __future__ import annotations

import json

import pytest

from app.qa_engine.checks.css_audit import CSSAuditCheck


@pytest.fixture
def check() -> CSSAuditCheck:
    return CSSAuditCheck()


class TestCSSAuditCheck:
    """Test suite for CSSAuditCheck."""

    async def test_simple_html_high_coverage(self, check: CSSAuditCheck) -> None:
        """Simple HTML with universally-supported properties should score high."""
        html = "<html><head><style>body { color: #000; font-size: 16px; }</style></head><body>Hello</body></html>"
        result = await check.run(html)
        assert result.check_name == "css_audit"
        assert result.passed is True
        assert result.score >= 0.8
        details = json.loads(result.details or "{}")
        assert "compatibility_matrix" in details
        assert "client_coverage_score" in details

    async def test_removed_property_detected(self, check: CSSAuditCheck) -> None:
        """Properties removed by the compiler should appear in the matrix."""
        from app.email_engine.css_compiler.compiler import OptimizedCSS

        pre_computed = OptimizedCSS(
            html="<html><head></head><body>Hello</body></html>",
            removed_properties=["flex"],
            conversions=[],
            warnings=[],
            optimize_time_ms=0.0,
        )
        html = (
            "<html><head><style>div { flex: 1; }</style></head><body><div>Hello</div></body></html>"
        )
        result = await check.run(html, compilation_result=pre_computed)
        details = json.loads(result.details or "{}")
        assert "flex" in details["removed_properties"]
        matrix = details.get("compatibility_matrix", {})
        # flex should appear in the matrix for all clients
        for client_data in matrix.values():
            assert "flex" in client_data

    async def test_empty_css_full_coverage(self, check: CSSAuditCheck) -> None:
        """HTML with no CSS should get 100% coverage."""
        html = "<html><head></head><body>Hello</body></html>"
        result = await check.run(html)
        assert result.passed is True
        assert result.score >= 0.9  # No properties = no issues
        details = json.loads(result.details or "{}")
        assert details.get("error_count", 0) == 0

    async def test_custom_target_clients(self, check: CSSAuditCheck) -> None:
        """Custom target_clients should be respected via config params."""
        from app.qa_engine.check_config import QACheckConfig

        html = "<html><head><style>div { color: red; }</style></head><body><div>Test</div></body></html>"
        config = QACheckConfig(params={"target_clients": ["gmail-web"]})
        result = await check.run(html, config)
        details = json.loads(result.details or "{}")
        assert list(details["compatibility_matrix"].keys()) == ["gmail-web"]
        assert list(details["client_coverage_score"].keys()) == ["gmail-web"]

    async def test_pre_computed_compilation_result(self, check: CSSAuditCheck) -> None:
        """Passing a pre-computed OptimizedCSS should skip re-compilation."""
        from app.email_engine.css_compiler.compiler import OptimizedCSS

        pre_computed = OptimizedCSS(
            html="<html><head></head><body>Test</body></html>",
            removed_properties=["flex"],
            conversions=[],
            warnings=[],
            optimize_time_ms=0.0,
        )
        result = await check.run(
            "<html><head><style>div { flex: 1; }</style></head><body><div>Test</div></body></html>",
            compilation_result=pre_computed,
        )
        details = json.loads(result.details or "{}")
        assert "flex" in details["removed_properties"]

    async def test_details_is_valid_json(self, check: CSSAuditCheck) -> None:
        """Details field should be valid parseable JSON."""
        html = "<html><head><style>body { margin: 0; padding: 0; color: #333; }</style></head><body>Hello</body></html>"
        result = await check.run(html)
        assert result.details is not None
        details = json.loads(result.details)
        assert isinstance(details, dict)
        assert "overall_coverage_score" in details
        assert isinstance(details["overall_coverage_score"], (int, float))

    async def test_score_between_zero_and_one(self, check: CSSAuditCheck) -> None:
        """Score should always be between 0 and 1."""
        html = "<html><head><style>div { border-radius: 8px; box-shadow: 0 0 5px #ccc; flex: 1; grid-template-columns: 1fr 1fr; }</style></head><body><div>Test</div></body></html>"
        result = await check.run(html)
        assert 0.0 <= result.score <= 1.0
