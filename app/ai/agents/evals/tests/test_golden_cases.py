"""Tests for golden CI test cases."""

from app.ai.agents.evals.golden_cases import GOLDEN_CASES, GoldenCase, run_golden_cases


class TestGoldenCaseDefinitions:
    def test_all_cases_have_unique_names(self) -> None:
        names = [c.name for c in GOLDEN_CASES]
        assert len(names) == len(set(names))

    def test_all_cases_have_template_name(self) -> None:
        for case in GOLDEN_CASES:
            assert case.template_name, f"Case {case.name} missing template_name"

    def test_minimum_case_count(self) -> None:
        assert len(GOLDEN_CASES) >= 5, "Need at least 5 golden cases"

    def test_case_is_frozen_dataclass(self) -> None:
        case = GoldenCase(name="test", template_name="newsletter_1col")
        assert case.name == "test"


class TestRunGoldenCases:
    def test_runs_all_cases(self) -> None:
        results = run_golden_cases(verbose=False)
        assert len(results) == len(GOLDEN_CASES)

    def test_all_templates_found(self) -> None:
        results = run_golden_cases(verbose=False)
        for r in results:
            assert r.template_found, f"Template not found for case: {r.case_name}"

    def test_all_golden_cases_pass(self) -> None:
        results = run_golden_cases(verbose=False)
        failed = [r for r in results if not r.passed]
        failure_details = "; ".join(f"{r.case_name}: {', '.join(r.failures)}" for r in failed)
        assert not failed, f"Golden cases failed: {failure_details}"
