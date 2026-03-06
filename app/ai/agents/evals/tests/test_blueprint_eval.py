"""Tests for blueprint eval module."""

from app.ai.agents.evals.blueprint_eval import BLUEPRINT_TEST_BRIEFS, print_summary
from app.ai.agents.evals.schemas import BlueprintEvalTrace


def _trace(
    run_id: str = "bp-001",
    qa_passed: bool | None = True,
    total_steps: int = 5,
    total_retries: int = 0,
    total_tokens: int = 1000,
    elapsed_seconds: float = 10.0,
    error: str | None = None,
) -> BlueprintEvalTrace:
    return BlueprintEvalTrace(
        run_id=run_id,
        blueprint_name="campaign",
        brief="Test brief",
        total_steps=total_steps,
        total_retries=total_retries,
        qa_passed=qa_passed,
        final_html_length=5000,
        total_tokens=total_tokens,
        elapsed_seconds=elapsed_seconds,
        node_trace=[],
        error=error,
    )


class TestBlueprintTestBriefs:
    def test_has_five_briefs(self) -> None:
        assert len(BLUEPRINT_TEST_BRIEFS) == 5

    def test_all_briefs_have_required_fields(self) -> None:
        for brief in BLUEPRINT_TEST_BRIEFS:
            assert "id" in brief
            assert "name" in brief
            assert "brief" in brief
            assert brief["id"].startswith("bp-")

    def test_unique_ids(self) -> None:
        ids = [b["id"] for b in BLUEPRINT_TEST_BRIEFS]
        assert len(ids) == len(set(ids))


class TestBlueprintEvalTrace:
    def test_successful_trace(self) -> None:
        t = _trace(qa_passed=True, total_steps=5, total_retries=1)
        assert t.qa_passed is True
        assert t.error is None

    def test_error_trace(self) -> None:
        t = _trace(error="BlueprintEscalatedError: scaffolder exhausted retries")
        assert t.error is not None
        assert t.qa_passed is True  # Set by caller; error overrides semantically


class TestPrintSummary:
    def test_prints_without_error(self) -> None:
        traces = [
            _trace(qa_passed=True, total_steps=4, total_tokens=800),
            _trace(qa_passed=False, total_steps=6, total_tokens=1200),
        ]
        print_summary(traces)

    def test_handles_empty_traces(self) -> None:
        print_summary([])

    def test_handles_all_errors(self) -> None:
        traces = [_trace(error="fail", qa_passed=None)]
        print_summary(traces)
