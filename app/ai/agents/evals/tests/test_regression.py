"""Tests for regression detection module."""

from app.ai.agents.evals.regression import (
    AGENT_REGRESSION_TOLERANCE,
    build_regression_report,
    compare_pass_rates,
    is_agent_regression,
)


class TestComparePassRates:
    def test_no_change(self) -> None:
        current = {"scaffolder": {"a": 0.8, "b": 0.9}}
        baseline = {"scaffolder": {"a": 0.8, "b": 0.9}}
        reports = compare_pass_rates(current, baseline, tolerance=0.10)
        assert len(reports) == 1
        assert reports[0].is_regression is False
        assert reports[0].regressed_criteria == []
        assert reports[0].improved_criteria == []

    def test_within_tolerance(self) -> None:
        # Drop of 2pp: within both criterion tolerance (10%) and agent tolerance (3pp)
        current = {"scaffolder": {"a": 0.78}}
        baseline = {"scaffolder": {"a": 0.80}}
        reports = compare_pass_rates(current, baseline, tolerance=0.10)
        assert reports[0].is_regression is False  # -0.02 < -0.03 (agent) and < -0.10 (criterion)

    def test_beyond_tolerance(self) -> None:
        current = {"scaffolder": {"a": 0.60}}
        baseline = {"scaffolder": {"a": 0.80}}
        reports = compare_pass_rates(current, baseline, tolerance=0.10)
        assert reports[0].is_regression is True
        assert reports[0].regressed_criteria == ["a"]

    def test_improvement(self) -> None:
        current = {"scaffolder": {"a": 1.0}}
        baseline = {"scaffolder": {"a": 0.80}}
        reports = compare_pass_rates(current, baseline, tolerance=0.10)
        assert reports[0].is_regression is False
        assert reports[0].improved_criteria == ["a"]

    def test_new_agent_no_baseline(self) -> None:
        current = {"new_agent": {"a": 0.9}}
        baseline: dict[str, dict[str, float]] = {}
        reports = compare_pass_rates(current, baseline, tolerance=0.10)
        assert len(reports) == 1
        assert reports[0].is_regression is False
        assert reports[0].improved_criteria == ["a"]

    def test_multiple_agents(self) -> None:
        current = {
            "scaffolder": {"a": 0.50},  # Regressed
            "dark_mode": {"a": 0.95},  # Improved
        }
        baseline = {
            "scaffolder": {"a": 0.80},
            "dark_mode": {"a": 0.80},
        }
        reports = compare_pass_rates(current, baseline, tolerance=0.10)
        scaffolder = next(r for r in reports if r.agent == "scaffolder")
        dark_mode = next(r for r in reports if r.agent == "dark_mode")
        assert scaffolder.is_regression is True
        assert dark_mode.is_regression is False

    def test_multiple_criteria_mixed(self) -> None:
        current = {"scaffolder": {"a": 0.50, "b": 0.95, "c": 0.80}}
        baseline = {"scaffolder": {"a": 0.80, "b": 0.80, "c": 0.80}}
        reports = compare_pass_rates(current, baseline, tolerance=0.10)
        assert reports[0].is_regression is True
        assert reports[0].regressed_criteria == ["a"]
        assert reports[0].improved_criteria == ["b"]

    def test_agent_level_3pp_regression(self) -> None:
        """A 5pp agent-level drop triggers regression even when within criterion tolerance."""
        current = {"scaffolder": {"a": 0.75}}
        baseline = {"scaffolder": {"a": 0.80}}
        reports = compare_pass_rates(current, baseline, tolerance=0.10)
        # -5pp exceeds AGENT_REGRESSION_TOLERANCE (3pp), so this IS a regression
        assert reports[0].is_regression is True
        # But no individual criterion regressed beyond the 10% criterion tolerance
        assert reports[0].regressed_criteria == []


class TestIsAgentRegression:
    def test_below_threshold(self) -> None:
        assert is_agent_regression(0.80, 0.78) is False  # 2pp < 3pp

    def test_at_threshold(self) -> None:
        # 2.9pp drop — just under the 3pp boundary
        assert is_agent_regression(0.80, 0.771) is False

    def test_above_threshold(self) -> None:
        assert is_agent_regression(0.80, 0.76) is True  # 4pp > 3pp

    def test_constant_value(self) -> None:
        assert AGENT_REGRESSION_TOLERANCE == 0.03


class TestBuildRegressionReport:
    def test_no_regression(self) -> None:
        current = {"scaffolder": {"a": 0.80}}
        baseline = {"scaffolder": {"a": 0.80}}
        reports = compare_pass_rates(current, baseline, tolerance=0.10)
        report = build_regression_report(reports)
        assert report["has_regression"] is False
        assert report["agents_regressed"] == 0

    def test_with_regression(self) -> None:
        current = {"scaffolder": {"a": 0.50}}
        baseline = {"scaffolder": {"a": 0.80}}
        reports = compare_pass_rates(current, baseline, tolerance=0.10)
        report = build_regression_report(reports)
        assert report["has_regression"] is True
        assert report["agents_regressed"] == 1
        assert report["details"][0]["regressed_criteria"] == ["a"]
