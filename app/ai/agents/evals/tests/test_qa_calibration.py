"""Tests for QA gate calibration module."""

from app.ai.agents.evals.qa_calibration import build_qa_report, calibrate_qa
from app.ai.agents.evals.schemas import HumanLabel, QACalibrationResult


def _label(
    trace_id: str, criterion: str, human_pass: bool, agent: str = "scaffolder"
) -> HumanLabel:
    return HumanLabel(
        trace_id=trace_id,
        agent=agent,
        criterion=criterion,
        human_pass=human_pass,
    )


class TestCalibrateQA:
    def test_perfect_agreement(self) -> None:
        qa_results = {
            "t1": {"dark_mode": True, "accessibility": False},
        }
        labels = [
            _label("t1", "dark_mode", True),
            _label("t1", "accessibility", False),
        ]
        results = calibrate_qa(qa_results, labels)
        assert len(results) == 2
        for r in results:
            assert r.agreement_rate == 1.0
            assert r.false_pass_rate == 0.0
            assert r.false_fail_rate == 0.0

    def test_all_disagreement(self) -> None:
        qa_results = {"t1": {"dark_mode": True}}
        labels = [_label("t1", "dark_mode", False)]
        results = calibrate_qa(qa_results, labels)
        assert results[0].agreement_rate == 0.0
        assert results[0].false_pass_rate == 1.0

    def test_false_fail(self) -> None:
        qa_results = {"t1": {"dark_mode": False}}
        labels = [_label("t1", "dark_mode", True)]
        results = calibrate_qa(qa_results, labels)
        assert results[0].false_fail_rate == 1.0

    def test_ignores_non_qa_criteria(self) -> None:
        qa_results = {"t1": {"dark_mode": True}}
        labels = [
            _label("t1", "brief_fidelity", True),  # Not a QA check name
            _label("t1", "dark_mode", True),
        ]
        results = calibrate_qa(qa_results, labels)
        assert len(results) == 1
        assert results[0].check_name == "dark_mode"

    def test_skips_missing_traces(self) -> None:
        qa_results = {"t1": {"dark_mode": True}}
        labels = [_label("t2", "dark_mode", True)]  # t2 not in qa_results
        results = calibrate_qa(qa_results, labels)
        assert len(results) == 0

    def test_multiple_traces(self) -> None:
        qa_results = {
            "t1": {"dark_mode": True},
            "t2": {"dark_mode": False},
            "t3": {"dark_mode": True},
        }
        labels = [
            _label("t1", "dark_mode", True),  # Agree
            _label("t2", "dark_mode", False),  # Agree
            _label("t3", "dark_mode", False),  # Disagree (false pass)
        ]
        results = calibrate_qa(qa_results, labels)
        assert len(results) == 1
        r = results[0]
        assert r.total == 3
        assert abs(r.agreement_rate - 2 / 3) < 0.001
        assert abs(r.false_pass_rate - 1 / 3) < 0.001


class TestBuildQAReport:
    def test_average_agreement(self) -> None:
        results = [
            QACalibrationResult("dark_mode", 0.80, 0.10, 0.10, 10),
            QACalibrationResult("accessibility", 0.60, 0.20, 0.20, 10),
        ]
        report = build_qa_report(results)
        assert report["average_agreement"] == 0.7
        assert report["checks_evaluated"] == 2

    def test_needs_tuning_threshold(self) -> None:
        results = [
            QACalibrationResult("dark_mode", 0.80, 0.10, 0.10, 10),
            QACalibrationResult("accessibility", 0.60, 0.20, 0.20, 10),  # < 0.75
        ]
        report = build_qa_report(results)
        assert report["checks_needing_tuning"] == 1
        assert report["needs_tuning"][0]["check_name"] == "accessibility"

    def test_empty_results(self) -> None:
        report = build_qa_report([])
        assert report["average_agreement"] == 0.0
        assert report["checks_evaluated"] == 0
