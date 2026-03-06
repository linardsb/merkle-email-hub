"""Tests for dry-run eval pipeline (mock traces, verdicts, full pipeline)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.ai.agents.evals.mock_traces import (
    AGENT_CRITERIA,
    MOCK_HTML,
    generate_mock_blueprint_trace,
    generate_mock_trace,
    generate_mock_verdict,
)


def _make_case(case_id: str, agent: str = "scaffolder") -> dict[str, Any]:
    return {
        "id": case_id,
        "agent": agent,
        "brief": "Test brief",
        "dimensions": ["layout_complexity"],
        "expected_challenges": ["table_layout"],
    }


class TestMockTraces:
    def test_mock_trace_structure(self) -> None:
        case = _make_case("scaff-001")
        trace = generate_mock_trace(case, "scaffolder")

        assert trace["id"] == "scaff-001"
        assert trace["agent"] == "scaffolder"
        assert trace["output"] is not None
        assert "html" in trace["output"]
        assert trace["output"]["model"] == "dry-run-mock"
        assert trace["error"] is None
        assert trace["elapsed_seconds"] == 0.01
        assert "timestamp" in trace
        assert "dimensions" in trace
        assert "expected_challenges" in trace

    def test_mock_trace_html_is_valid(self) -> None:
        case = _make_case("scaff-001")
        trace = generate_mock_trace(case, "scaffolder")
        html: str = trace["output"]["html"]

        assert "<!DOCTYPE html>" in html
        assert 'lang="en"' in html
        assert "<!--[if mso]>" in html
        assert 'role="presentation"' in html


class TestMockVerdicts:
    def test_mock_verdict_structure(self) -> None:
        trace = generate_mock_trace(_make_case("scaff-001"), "scaffolder")
        criteria = AGENT_CRITERIA["scaffolder"]
        verdict = generate_mock_verdict(trace, criteria)

        assert verdict["trace_id"] == "scaff-001"
        assert verdict["agent"] == "scaffolder"
        assert isinstance(verdict["overall_pass"], bool)
        assert verdict["error"] is None
        assert len(verdict["criteria_results"]) == 5
        for cr in verdict["criteria_results"]:
            assert "criterion" in cr
            assert "passed" in cr
            assert "reasoning" in cr

    def test_mock_verdict_deterministic(self) -> None:
        trace = generate_mock_trace(_make_case("scaff-001"), "scaffolder")
        criteria = AGENT_CRITERIA["scaffolder"]

        v1 = generate_mock_verdict(trace, criteria)
        v2 = generate_mock_verdict(trace, criteria)

        for cr1, cr2 in zip(v1["criteria_results"], v2["criteria_results"], strict=True):
            assert cr1["passed"] == cr2["passed"]

    def test_mock_verdict_has_failures(self) -> None:
        """Generate enough verdicts to ensure at least one failure exists."""
        all_results: list[bool] = []
        for i in range(20):
            trace = generate_mock_trace(_make_case(f"scaff-{i:03d}"), "scaffolder")
            verdict = generate_mock_verdict(trace, AGENT_CRITERIA["scaffolder"])
            for cr in verdict["criteria_results"]:
                all_results.append(cr["passed"])

        assert not all(all_results), "Expected some failures in mock verdicts"
        assert any(all_results), "Expected some passes in mock verdicts"


class TestMockBlueprintTraces:
    def test_mock_blueprint_trace_structure(self) -> None:
        brief_def = {
            "id": "bp-001",
            "name": "happy_path",
            "brief": "Create a simple promo email.",
        }
        trace = generate_mock_blueprint_trace(brief_def)

        assert trace["run_id"] == "bp-001"
        assert trace["blueprint_name"] == "campaign"
        assert isinstance(trace["total_steps"], int)
        assert isinstance(trace["total_retries"], int)
        assert isinstance(trace["qa_passed"], bool)
        assert trace["error"] is None
        assert len(trace["node_trace"]) == 2


class TestFullDryRunPipeline:
    def test_end_to_end_pipeline(self) -> None:
        """Exercise: mock traces -> mock verdicts -> error_analysis -> scaffold_labels."""
        from app.ai.agents.evals.error_analysis import build_analysis_report
        from app.ai.agents.evals.scaffold_labels import scaffold_labels

        # Step 1: Generate traces for scaffolder
        cases = [_make_case(f"scaff-{i:03d}") for i in range(5)]
        traces = [generate_mock_trace(c, "scaffolder") for c in cases]

        # Step 2: Generate verdicts
        criteria = AGENT_CRITERIA["scaffolder"]
        verdicts = [generate_mock_verdict(t, criteria) for t in traces]

        # Step 3: Error analysis
        report = build_analysis_report(verdicts)

        assert report["summary"]["total_traces"] == 5
        assert "pass_rates" in report
        assert "scaffolder" in report["pass_rates"]
        assert "failure_clusters" in report

        # Step 4: Scaffold labels
        labels = scaffold_labels(verdicts, traces, include_qa_criteria=True)
        assert len(labels) > 0

        judge_labels = [lbl for lbl in labels if lbl["judge_pass"] is not None]
        qa_labels = [lbl for lbl in labels if lbl["judge_pass"] is None]
        assert len(judge_labels) > 0
        assert len(qa_labels) > 0

        # Verify labels are valid JSON-serializable
        for lbl in labels:
            json.dumps(lbl)

    def test_pipeline_with_all_agents(self) -> None:
        """Verify pipeline works for all 3 agents."""
        from app.ai.agents.evals.error_analysis import build_analysis_report

        all_verdicts: list[dict[str, Any]] = []
        for agent_name, criteria in AGENT_CRITERIA.items():
            cases = [_make_case(f"{agent_name}-{i:03d}", agent_name) for i in range(3)]
            traces = [generate_mock_trace(c, agent_name) for c in cases]
            for t in traces:
                all_verdicts.append(generate_mock_verdict(t, criteria))

        report = build_analysis_report(all_verdicts)
        assert report["summary"]["total_traces"] == 9
        assert len(report["pass_rates"]) == 3


@pytest.mark.asyncio
async def test_mock_html_passes_qa() -> None:
    """Run QA checks on MOCK_HTML — verify most checks pass."""
    from app.qa_engine.checks import ALL_CHECKS

    results: dict[str, bool] = {}
    for check in ALL_CHECKS:
        result = await check.run(MOCK_HTML)
        results[result.check_name] = result.passed

    passed_count = sum(1 for v in results.values() if v)
    total = len(results)

    # Most checks should pass on well-formed mock HTML
    assert passed_count >= total * 0.6, (
        f"Only {passed_count}/{total} QA checks passed on MOCK_HTML. "
        f"Failed: {[k for k, v in results.items() if not v]}"
    )
