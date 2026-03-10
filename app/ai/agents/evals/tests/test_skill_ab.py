"""Tests for SKILL.md A/B testing logic."""

from __future__ import annotations

import json

from app.ai.agents.evals.skill_ab import (
    build_ab_report,
    compare_variants,
)
from app.ai.agents.skill_override import (
    clear_all_overrides,
    clear_override,
    get_override,
    set_override,
)

# -- Skill Override Registry Tests --


class TestSkillOverride:
    def test_set_and_get_override(self) -> None:
        set_override("scaffolder", "test content")
        assert get_override("scaffolder") == "test content"
        clear_override("scaffolder")

    def test_get_override_returns_none_when_unset(self) -> None:
        assert get_override("nonexistent_agent") is None

    def test_clear_override(self) -> None:
        set_override("scaffolder", "test")
        clear_override("scaffolder")
        assert get_override("scaffolder") is None

    def test_clear_all_overrides(self) -> None:
        set_override("scaffolder", "a")
        set_override("dark_mode", "b")
        clear_all_overrides()
        assert get_override("scaffolder") is None
        assert get_override("dark_mode") is None

    def test_override_replaces_previous(self) -> None:
        set_override("scaffolder", "v1")
        set_override("scaffolder", "v2")
        assert get_override("scaffolder") == "v2"
        clear_override("scaffolder")


# -- Compare Variants Tests --


class TestCompareVariants:
    def test_identical_rates_recommend_merge(self) -> None:
        rates_a = {"scaffolder": {"brief_fidelity": 0.8, "layout_patterns": 0.9}}
        rates_b = {"scaffolder": {"brief_fidelity": 0.8, "layout_patterns": 0.9}}
        result = compare_variants("scaffolder", rates_a, rates_b, total_cases=12)
        assert result.recommendation == "merge"
        assert result.degraded_criteria == []
        assert result.overall_delta == 0.0

    def test_improvement_recommends_merge(self) -> None:
        rates_a = {"scaffolder": {"brief_fidelity": 0.6, "layout_patterns": 0.7}}
        rates_b = {"scaffolder": {"brief_fidelity": 0.8, "layout_patterns": 0.9}}
        result = compare_variants("scaffolder", rates_a, rates_b, total_cases=12)
        assert result.recommendation == "merge"
        assert len(result.improved_criteria) == 2
        assert result.overall_delta > 0

    def test_degradation_auto_rejects(self) -> None:
        rates_a = {"scaffolder": {"brief_fidelity": 0.8, "layout_patterns": 0.9}}
        rates_b = {"scaffolder": {"brief_fidelity": 0.7, "layout_patterns": 0.9}}
        result = compare_variants("scaffolder", rates_a, rates_b, total_cases=12)
        assert result.recommendation == "reject"
        assert "brief_fidelity" in result.degraded_criteria
        assert result.rejection_reason is not None

    def test_small_degradation_within_threshold_ok(self) -> None:
        """Drop of exactly 5% should NOT trigger rejection (< not <=)."""
        rates_a = {"scaffolder": {"brief_fidelity": 0.85}}
        rates_b = {"scaffolder": {"brief_fidelity": 0.80}}
        result = compare_variants("scaffolder", rates_a, rates_b, total_cases=12, threshold=0.05)
        assert result.recommendation == "merge"

    def test_insufficient_cases_needs_more_data(self) -> None:
        rates_a = {"scaffolder": {"brief_fidelity": 0.5}}
        rates_b = {"scaffolder": {"brief_fidelity": 0.9}}
        result = compare_variants("scaffolder", rates_a, rates_b, total_cases=5, min_cases=10)
        assert result.recommendation == "needs_more_data"

    def test_mixed_improvements_and_degradation_rejects(self) -> None:
        """Even one degraded criterion causes rejection."""
        rates_a = {
            "scaffolder": {
                "brief_fidelity": 0.7,
                "layout_patterns": 0.9,
                "mso_conditionals": 0.8,
            }
        }
        rates_b = {
            "scaffolder": {
                "brief_fidelity": 0.9,  # improved
                "layout_patterns": 0.75,  # degraded by 15%
                "mso_conditionals": 0.85,  # improved slightly
            }
        }
        result = compare_variants("scaffolder", rates_a, rates_b, total_cases=12)
        assert result.recommendation == "reject"
        assert "layout_patterns" in result.degraded_criteria
        assert "brief_fidelity" in result.improved_criteria

    def test_empty_rates_handled(self) -> None:
        result = compare_variants("scaffolder", {}, {}, total_cases=12)
        assert result.recommendation == "merge"
        assert result.criteria_deltas == []

    def test_new_criterion_in_proposed(self) -> None:
        """Proposed adds a new criterion not in current."""
        rates_a = {"scaffolder": {"brief_fidelity": 0.8}}
        rates_b = {"scaffolder": {"brief_fidelity": 0.8, "new_criterion": 0.9}}
        result = compare_variants("scaffolder", rates_a, rates_b, total_cases=12)
        assert result.recommendation == "merge"
        assert len(result.criteria_deltas) == 2

    def test_custom_threshold(self) -> None:
        rates_a = {"scaffolder": {"brief_fidelity": 0.8}}
        rates_b = {"scaffolder": {"brief_fidelity": 0.72}}
        # With 10% threshold, 8% drop is OK
        result = compare_variants("scaffolder", rates_a, rates_b, total_cases=12, threshold=0.10)
        assert result.recommendation == "merge"
        # With 5% threshold, 8% drop triggers rejection
        result2 = compare_variants("scaffolder", rates_a, rates_b, total_cases=12, threshold=0.05)
        assert result2.recommendation == "reject"


# -- Report Builder Tests --


class TestBuildABReport:
    def test_report_structure(self) -> None:
        rates_a = {"scaffolder": {"brief_fidelity": 0.8}}
        rates_b = {"scaffolder": {"brief_fidelity": 0.9}}
        result = compare_variants("scaffolder", rates_a, rates_b, total_cases=12)
        report = build_ab_report([result])
        assert "results" in report
        assert "degradation_threshold" in report
        assert "min_cases_required" in report
        assert len(report["results"]) == 1
        assert report["results"][0]["recommendation"] == "merge"

    def test_report_criteria_deltas_serializable(self) -> None:
        rates_a = {"scaffolder": {"a": 0.5, "b": 0.6}}
        rates_b = {"scaffolder": {"a": 0.7, "b": 0.3}}
        result = compare_variants("scaffolder", rates_a, rates_b, total_cases=12)
        report = build_ab_report([result])
        # Should be JSON-serializable
        json.dumps(report)

    def test_exit_code_logic(self) -> None:
        """Rejected result should produce exit code 1."""
        rates_a = {"scaffolder": {"brief_fidelity": 0.9}}
        rates_b = {"scaffolder": {"brief_fidelity": 0.5}}
        result = compare_variants("scaffolder", rates_a, rates_b, total_cases=12)
        assert result.recommendation == "reject"
        # CLI uses: sys.exit(1) if recommendation == "reject"
