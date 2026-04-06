"""Tests for evaluator schemas — verdict validation, score bounds, severity levels."""

import pytest
from pydantic import ValidationError

from app.ai.agents.evaluator.schemas import EvalIssue, EvalVerdict


class TestEvalVerdict:
    def test_eval_verdict_valid(self) -> None:
        """Accept/revise/reject verdicts with issues parse correctly."""
        for verdict_val in ("accept", "revise", "reject"):
            verdict = EvalVerdict(
                verdict=verdict_val,
                score=0.75,
                issues=[
                    EvalIssue(
                        severity="major",
                        category="layout",
                        description="Missing table structure",
                    )
                ],
                feedback="Needs work",
            )
            assert verdict.verdict == verdict_val
            assert len(verdict.issues) == 1
            assert verdict.issues[0].severity == "major"

    def test_eval_verdict_score_bounds(self) -> None:
        """Score must be between 0.0 and 1.0."""
        # Valid bounds
        EvalVerdict(verdict="accept", score=0.0)
        EvalVerdict(verdict="accept", score=1.0)

        # Out of bounds
        with pytest.raises(ValidationError):
            EvalVerdict(verdict="accept", score=-0.1)
        with pytest.raises(ValidationError):
            EvalVerdict(verdict="accept", score=1.1)

    def test_eval_issue_all_severities(self) -> None:
        """Critical, major, minor severities all accepted."""
        for sev in ("critical", "major", "minor"):
            issue = EvalIssue(
                severity=sev,
                category="test",
                description=f"A {sev} issue",
            )
            assert issue.severity == sev
            assert issue.location is None  # optional, defaults to None
