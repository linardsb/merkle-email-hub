"""Tests for LLM-friendly response formatters."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import patch

from pydantic import BaseModel

from app.mcp.formatting import (
    _apply_token_budget,
    format_css_compilation,
    format_knowledge_result,
    format_qa_result,
    format_simple_result,
    to_dict,
    truncate_html,
)


class TestTruncateHTML:
    def test_short_html_unchanged(self) -> None:
        html = "<p>Hello</p>"
        assert truncate_html(html) == html

    def test_long_html_truncated(self) -> None:
        html = "x" * 5000
        result = truncate_html(html, max_chars=100)
        assert len(result) < 5000
        assert "truncated" in result
        assert "4,900 chars remaining" in result

    def test_includes_total_size(self) -> None:
        html = "y" * 3000
        result = truncate_html(html, max_chars=1000)
        assert "3,000 total" in result


class TestFormatQAResult:
    def test_high_score_production_ready(self) -> None:
        result = format_qa_result(
            {"overall_score": 95, "passed": 11, "total": 11, "failed": 0, "checks": []}
        )
        assert "Production ready" in result
        assert "95/100" in result

    def test_low_score_shows_failures(self) -> None:
        result = format_qa_result(
            {
                "overall_score": 50,
                "passed": 5,
                "total": 11,
                "failed": 6,
                "checks": [
                    {"name": "CSS Support", "passed": False, "message": "3 unsupported properties"}
                ],
            }
        )
        assert "Significant issues" in result
        assert "CSS Support" in result

    def test_includes_next_steps(self) -> None:
        result = format_qa_result(
            {"overall_score": 70, "passed": 8, "total": 11, "failed": 3, "checks": []}
        )
        assert "Next steps" in result


class TestFormatKnowledgeResult:
    def test_empty_results(self) -> None:
        result = format_knowledge_result([])
        assert "No results found" in result

    def test_formats_results_with_relevance(self) -> None:
        result = format_knowledge_result(
            [
                {
                    "title": "CSS Grid in Email",
                    "score": 0.85,
                    "domain": "compatibility",
                    "content": "CSS Grid is...",
                },
            ]
        )
        assert "CSS Grid in Email" in result
        assert "85%" in result


class TestFormatCSSCompilation:
    def test_shows_size_reduction(self) -> None:
        result = format_css_compilation(
            {
                "original_size": 10000,
                "compiled_size": 6000,
                "conversions": [],
                "removed_properties": [],
            }
        )
        assert "40%" in result
        assert "10,000" in result


class TestFormatSimpleResult:
    def test_format_list_as_bullets(self) -> None:
        """List input formatted as bullet items."""
        result = format_simple_result(["item1", "item2", "item3"], "Test")
        assert "item1" in result
        assert "item2" in result
        assert "Test" in result


class TestToDict:
    def test_pydantic_model_to_dict(self) -> None:
        """Pydantic model converts to dict via model_dump."""

        class SampleModel(BaseModel):
            name: str
            value: int

        model = SampleModel(name="test", value=42)
        result = to_dict(model)
        assert result == {"name": "test", "value": 42}

    def test_dataclass_to_dict(self) -> None:
        """Dataclass converts to dict via asdict."""

        @dataclass
        class SampleDC:
            name: str
            value: int

        dc = SampleDC(name="test", value=42)
        result = to_dict(dc)
        assert result == {"name": "test", "value": 42}


class TestApplyTokenBudget:
    def test_truncation_with_marker(self) -> None:
        """Response exceeding budget is truncated with marker."""
        long_text = "x" * 50_000

        with patch("app.mcp.formatting.get_settings") as mock_settings:
            mock_settings.return_value.mcp.max_response_tokens = 100  # 400 chars
            result = _apply_token_budget(long_text)
            assert len(result) < 50_000
            assert "truncated to fit token budget" in result
