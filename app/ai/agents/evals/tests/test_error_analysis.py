"""Tests for error analysis module."""

from typing import Any

from app.ai.agents.evals.error_analysis import (
    build_analysis_report,
    cluster_failures,
    compute_pass_rates,
)


def _verdict(
    trace_id: str,
    agent: str,
    criteria: list[dict[str, Any]],
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "agent": agent,
        "overall_pass": all(c["passed"] for c in criteria),
        "criteria_results": criteria,
        "error": error,
    }


def _cr(name: str, passed: bool, reasoning: str = "ok") -> dict[str, Any]:
    return {"criterion": name, "passed": passed, "reasoning": reasoning}


class TestClusterFailures:
    def test_empty_verdicts(self) -> None:
        assert cluster_failures([]) == []

    def test_all_passing(self) -> None:
        verdicts = [
            _verdict("t1", "scaffolder", [_cr("brief_fidelity", True)]),
            _verdict("t2", "scaffolder", [_cr("brief_fidelity", True)]),
        ]
        assert cluster_failures(verdicts) == []

    def test_groups_by_agent_criterion(self) -> None:
        verdicts = [
            _verdict(
                "t1",
                "scaffolder",
                [_cr("brief_fidelity", False, "Missing hero")],
            ),
            _verdict(
                "t2",
                "scaffolder",
                [_cr("brief_fidelity", False, "No product cards")],
            ),
            _verdict(
                "t3",
                "dark_mode",
                [_cr("color_coherence", False, "White text on light")],
            ),
        ]
        clusters = cluster_failures(verdicts)
        assert len(clusters) == 2
        # Sorted by count desc: scaffolder:brief_fidelity (2) first
        assert clusters[0].cluster_id == "scaffolder:brief_fidelity"
        assert clusters[0].count == 2
        assert clusters[0].trace_ids == ["t1", "t2"]
        assert len(clusters[0].sample_reasonings) == 2

    def test_skips_error_verdicts(self) -> None:
        verdicts = [
            _verdict("t1", "scaffolder", [], error="LLM timeout"),
            _verdict(
                "t2",
                "scaffolder",
                [_cr("brief_fidelity", False, "Missing")],
            ),
        ]
        clusters = cluster_failures(verdicts)
        assert len(clusters) == 1
        assert clusters[0].trace_ids == ["t2"]

    def test_sample_reasonings_capped_at_three(self) -> None:
        verdicts = [
            _verdict(
                f"t{i}",
                "scaffolder",
                [_cr("brief_fidelity", False, f"Reason {i}")],
            )
            for i in range(5)
        ]
        clusters = cluster_failures(verdicts)
        assert len(clusters[0].sample_reasonings) == 3


class TestComputePassRates:
    def test_all_passing(self) -> None:
        verdicts = [
            _verdict("t1", "scaffolder", [_cr("a", True), _cr("b", True)]),
        ]
        rates = compute_pass_rates(verdicts)
        assert rates["scaffolder"]["a"] == 1.0
        assert rates["scaffolder"]["b"] == 1.0

    def test_mixed_results(self) -> None:
        verdicts = [
            _verdict("t1", "scaffolder", [_cr("a", True)]),
            _verdict("t2", "scaffolder", [_cr("a", False)]),
        ]
        rates = compute_pass_rates(verdicts)
        assert rates["scaffolder"]["a"] == 0.5

    def test_skips_errors(self) -> None:
        verdicts = [
            _verdict("t1", "scaffolder", [_cr("a", True)]),
            _verdict("t2", "scaffolder", [], error="fail"),
        ]
        rates = compute_pass_rates(verdicts)
        assert rates["scaffolder"]["a"] == 1.0

    def test_empty_verdicts(self) -> None:
        assert compute_pass_rates([]) == {}


class TestBuildAnalysisReport:
    def test_summary_counts(self) -> None:
        verdicts = [
            _verdict("t1", "scaffolder", [_cr("a", True)]),
            _verdict("t2", "scaffolder", [_cr("a", False, "bad")]),
            _verdict("t3", "scaffolder", [], error="timeout"),
        ]
        report = build_analysis_report(verdicts)
        s = report["summary"]
        assert s["total_traces"] == 3
        assert s["passed"] == 1
        assert s["failed"] == 1
        assert s["errors"] == 1
        assert s["overall_pass_rate"] == 0.5  # 1 passed / 2 non-error

    def test_top_failures_limited_to_three(self) -> None:
        verdicts = [
            _verdict(
                f"t{i}",
                "scaffolder",
                [_cr(f"crit_{j}", False, f"r{j}") for j in range(5)],
            )
            for i in range(3)
        ]
        report = build_analysis_report(verdicts)
        assert len(report["top_failures"]) == 3

    def test_empty_verdicts(self) -> None:
        report = build_analysis_report([])
        assert report["summary"]["total_traces"] == 0
        assert report["summary"]["overall_pass_rate"] == 0.0
