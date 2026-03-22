# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
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
        html = '<html><head><style>td { flex: 1; }</style></head><body><table role="presentation"><tr><td>Hello</td></tr></table></body></html>'
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

        html = '<html><head><style>td { color: red; }</style></head><body><table role="presentation"><tr><td>Test</td></tr></table></body></html>'
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
            '<html><head><style>td { flex: 1; }</style></head><body><table role="presentation"><tr><td>Test</td></tr></table></body></html>',
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
        html = '<html><head><style>td { border-radius: 8px; box-shadow: 0 0 5px #ccc; flex: 1; grid-template-columns: 1fr 1fr; }</style></head><body><table role="presentation"><tr><td>Test</td></tr></table></body></html>'
        result = await check.run(html)
        assert 0.0 <= result.score <= 1.0

    async def test_removed_properties_tracked_in_details(self, check: CSSAuditCheck) -> None:
        """Pre-computed removed properties should appear in details."""
        from app.email_engine.css_compiler.compiler import OptimizedCSS

        pre_computed = OptimizedCSS(
            html='<html><head></head><body><table role="presentation"><tr><td>Hello</td></tr></table></body></html>',
            removed_properties=["flex"],
            conversions=[],
            warnings=[],
            optimize_time_ms=0.0,
        )
        html = '<html><head><style>td { flex: 1; }</style></head><body><table role="presentation"><tr><td>Hello</td></tr></table></body></html>'
        result = await check.run(html, compilation_result=pre_computed)
        details = json.loads(result.details or "{}")
        assert "flex" in details.get("removed_properties", [])

    async def test_conversions_passed_through_in_details(self, check: CSSAuditCheck) -> None:
        """Pre-computed conversions should appear in details."""
        from app.email_engine.css_compiler.compiler import OptimizedCSS
        from app.email_engine.css_compiler.conversions import CSSConversion

        conversion = CSSConversion(
            original_property="display",
            original_value="flex",
            replacement_property="display",
            replacement_value="block",
            reason="Fallback conversion",
            affected_clients=("outlook_2019",),
        )
        pre_computed = OptimizedCSS(
            html='<html><head></head><body><table role="presentation"><tr><td>Hello</td></tr></table></body></html>',
            removed_properties=[],
            conversions=[conversion],
            warnings=[],
            optimize_time_ms=0.0,
        )
        html = '<html><head><style>td { display: flex; }</style></head><body><table role="presentation"><tr><td>Hello</td></tr></table></body></html>'
        result = await check.run(html, compilation_result=pre_computed)
        details = json.loads(result.details or "{}")
        conversions = details.get("conversions", [])
        assert len(conversions) > 0
        assert conversions[0]["original_property"] == "display"

    async def test_conversion_details_have_correct_structure(self, check: CSSAuditCheck) -> None:
        """Conversion details should contain expected fields."""
        from app.email_engine.css_compiler.compiler import OptimizedCSS
        from app.email_engine.css_compiler.conversions import CSSConversion

        conversion = CSSConversion(
            original_property="display",
            original_value="flex",
            replacement_property="display",
            replacement_value="block",
            reason="Fallback",
            affected_clients=("outlook_2019",),
        )
        pre_computed = OptimizedCSS(
            html='<html><head></head><body><table role="presentation"><tr><td>Hello</td></tr></table></body></html>',
            removed_properties=[],
            conversions=[conversion],
            warnings=[],
            optimize_time_ms=0.0,
        )
        html = '<html><head><style>td { display: flex; }</style></head><body><table role="presentation"><tr><td>Hello</td></tr></table></body></html>'
        result = await check.run(html, compilation_result=pre_computed)
        details = json.loads(result.details or "{}")
        conversions = details.get("conversions", [])
        assert len(conversions) > 0
        conv = conversions[0]
        assert conv["original_property"] == "display"
        assert conv["replacement_property"] == "display"
        assert conv["replacement_value"] == "block"
        assert "affected_clients" in conv

    async def test_empty_html_graceful(self, check: CSSAuditCheck) -> None:
        """Completely empty HTML should not crash."""
        result = await check.run("")
        assert result.passed is True

    async def test_per_client_coverage_score_calculation(self, check: CSSAuditCheck) -> None:
        """client_coverage_score dict should have entries for each target client."""
        html = "<html><head><style>body { color: #000; margin: 0; }</style></head><body>Hello</body></html>"
        result = await check.run(html)
        details = json.loads(result.details or "{}")
        scores = details.get("client_coverage_score", {})
        assert len(scores) > 0
        for client_id, score in scores.items():
            assert 0 <= score <= 100, f"{client_id} score {score} out of range"

    async def test_overall_coverage_score_is_numeric(self, check: CSSAuditCheck) -> None:
        """Overall coverage score should be a numeric value."""
        html = "<html><head><style>body { color: #000; padding: 10px; }</style></head><body>Hello</body></html>"
        result = await check.run(html)
        details = json.loads(result.details or "{}")
        overall = details.get("overall_coverage_score")
        assert isinstance(overall, (int, float))
        assert 0 <= overall <= 100

    async def test_css_audit_check_name_in_result(self, check: CSSAuditCheck) -> None:
        """Check name should always be 'css_audit'."""
        html = "<html><head><style>body { color: red; }</style></head><body>Hi</body></html>"
        result = await check.run(html)
        assert result.check_name == "css_audit"
