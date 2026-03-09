"""Tests for eval-informed failure warnings module."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.ai.agents.evals.failure_warnings import (
    _build_warnings_for_agent,
    _format_criterion_name,
    clear_cache,
    get_failure_warnings,
)


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Clear module-level cache before each test."""
    clear_cache()


def _make_analysis(
    pass_rates: dict[str, dict[str, float]] | None = None,
    failure_clusters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a minimal analysis.json structure."""
    return {
        "summary": {
            "total_traces": 10,
            "passed": 5,
            "failed": 5,
            "errors": 0,
            "overall_pass_rate": 0.5,
        },
        "pass_rates": pass_rates or {},
        "failure_clusters": failure_clusters or [],
        "top_failures": [],
    }


class TestFormatCriterionName:
    def test_simple(self) -> None:
        assert _format_criterion_name("brief_fidelity") == "Brief Fidelity"

    def test_abbreviations(self) -> None:
        assert (
            _format_criterion_name("mso_conditional_correctness") == "MSO Conditional Correctness"
        )
        assert _format_criterion_name("html_preservation") == "HTML Preservation"
        assert _format_criterion_name("css_support") == "CSS Support"
        assert _format_criterion_name("vml_wellformedness") == "VML Wellformedness"

    def test_single_word(self) -> None:
        assert _format_criterion_name("grammar") == "Grammar"


class TestBuildWarningsForAgent:
    def test_no_rates_returns_none(self) -> None:
        assert _build_warnings_for_agent("scaffolder", {}, []) is None

    def test_all_above_threshold_returns_none(self) -> None:
        rates = {"scaffolder": {"brief_fidelity": 0.9, "code_quality": 0.95}}
        assert _build_warnings_for_agent("scaffolder", rates, []) is None

    def test_below_threshold_included(self) -> None:
        rates = {"scaffolder": {"mso_conditionals": 0.5, "brief_fidelity": 0.9}}
        clusters = [
            {
                "agent": "scaffolder",
                "criterion": "mso_conditionals",
                "count": 5,
                "sample_reasonings": ["Missing <!--[if mso]> wrappers"],
            },
        ]
        result = _build_warnings_for_agent("scaffolder", rates, clusters)
        assert result is not None
        assert "MSO Conditionals" in result
        assert "50%" in result
        assert "5 failures" in result
        assert "Missing <!--[if mso]> wrappers" in result

    def test_sorted_worst_first(self) -> None:
        rates = {"scaffolder": {"criterion_a": 0.3, "criterion_b": 0.6}}
        result = _build_warnings_for_agent("scaffolder", rates, [])
        assert result is not None
        # criterion_a (30%) should appear before criterion_b (60%)
        idx_a = result.index("Criterion A")
        idx_b = result.index("Criterion B")
        assert idx_a < idx_b

    def test_max_warnings_cap(self) -> None:
        rates = {"scaffolder": {f"criterion_{i}": 0.1 * i for i in range(8)}}
        result = _build_warnings_for_agent("scaffolder", rates, [])
        assert result is not None
        # Should cap at 5 warnings (count bold entries, not header text)
        assert result.count("failures):**") == 5

    def test_other_agent_clusters_excluded(self) -> None:
        rates = {"scaffolder": {"mso_conditionals": 0.5}}
        clusters = [
            {
                "agent": "dark_mode",
                "criterion": "meta_tags",
                "count": 5,
                "sample_reasonings": ["Missing meta"],
            },
        ]
        result = _build_warnings_for_agent("scaffolder", rates, clusters)
        assert result is not None
        assert "meta_tags" not in result.lower()

    def test_mock_reasoning_cleaned(self) -> None:
        rates = {"scaffolder": {"mso_conditionals": 0.5}}
        clusters = [
            {
                "agent": "scaffolder",
                "criterion": "mso_conditionals",
                "count": 3,
                "sample_reasonings": ["Fail: mock evaluation of mso_conditionals for scaff-001"],
            },
        ]
        result = _build_warnings_for_agent("scaffolder", rates, clusters)
        assert result is not None
        assert "mock evaluation" not in result


class TestGetFailureWarnings:
    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        result = get_failure_warnings("scaffolder", analysis_path=tmp_path / "nonexistent.json")
        assert result is None

    def test_invalid_json_returns_none(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "analysis.json"
        bad_file.write_text("not json{{{")
        result = get_failure_warnings("scaffolder", analysis_path=bad_file)
        assert result is None

    def test_loads_real_format(self, tmp_path: Path) -> None:
        analysis = _make_analysis(
            pass_rates={"scaffolder": {"mso_conditionals": 0.58, "brief_fidelity": 0.83}},
            failure_clusters=[
                {
                    "cluster_id": "scaffolder:mso_conditionals",
                    "agent": "scaffolder",
                    "criterion": "mso_conditionals",
                    "pattern": "Missing MSO conditional comments",
                    "count": 5,
                    "trace_ids": ["s1", "s2", "s3", "s4", "s5"],
                    "sample_reasonings": ["MSO wrappers missing around table elements"],
                },
            ],
        )
        analysis_file = tmp_path / "analysis.json"
        analysis_file.write_text(json.dumps(analysis))

        result = get_failure_warnings("scaffolder", analysis_path=analysis_file)
        assert result is not None
        assert "MSO Conditionals" in result
        assert "58%" in result

    def test_caching_by_mtime(self, tmp_path: Path) -> None:
        analysis = _make_analysis(pass_rates={"scaffolder": {"criterion_a": 0.5}})
        analysis_file = tmp_path / "analysis.json"
        analysis_file.write_text(json.dumps(analysis))

        result1 = get_failure_warnings("scaffolder", analysis_path=analysis_file)
        result2 = get_failure_warnings("scaffolder", analysis_path=analysis_file)
        assert result1 == result2  # Same object from cache

    def test_unknown_agent_returns_none(self, tmp_path: Path) -> None:
        analysis = _make_analysis(pass_rates={"scaffolder": {"criterion_a": 0.5}})
        analysis_file = tmp_path / "analysis.json"
        analysis_file.write_text(json.dumps(analysis))

        result = get_failure_warnings("nonexistent_agent", analysis_path=analysis_file)
        assert result is None

    def test_agent_all_passing_returns_none(self, tmp_path: Path) -> None:
        analysis = _make_analysis(
            pass_rates={"scaffolder": {"brief_fidelity": 0.95, "code_quality": 0.90}}
        )
        analysis_file = tmp_path / "analysis.json"
        analysis_file.write_text(json.dumps(analysis))

        result = get_failure_warnings("scaffolder", analysis_path=analysis_file)
        assert result is None
