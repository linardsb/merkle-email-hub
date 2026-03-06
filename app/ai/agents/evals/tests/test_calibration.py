"""Tests for judge calibration module."""

from app.ai.agents.evals.calibration import build_calibration_report, calibrate
from app.ai.agents.evals.schemas import CalibrationResult, HumanLabel


def _label(trace_id: str, agent: str, criterion: str, human_pass: bool) -> HumanLabel:
    return HumanLabel(
        trace_id=trace_id,
        agent=agent,
        criterion=criterion,
        human_pass=human_pass,
    )


class TestCalibrationResult:
    def test_perfect_agreement(self) -> None:
        r = CalibrationResult(
            agent="scaffolder",
            criterion="brief_fidelity",
            true_positives=8,
            true_negatives=2,
            false_positives=0,
            false_negatives=0,
            total=10,
        )
        assert r.tpr == 1.0
        assert r.tnr == 1.0
        assert r.meets_targets is True

    def test_all_false_positives(self) -> None:
        r = CalibrationResult(
            agent="scaffolder",
            criterion="brief_fidelity",
            true_positives=0,
            true_negatives=0,
            false_positives=5,
            false_negatives=0,
            total=5,
        )
        assert r.tpr == 0.0
        assert r.tnr == 0.0

    def test_meets_targets_boundary_tpr(self) -> None:
        # TPR = 85/100 = 0.85 exactly -> should pass
        r = CalibrationResult(
            agent="a",
            criterion="c",
            true_positives=85,
            true_negatives=80,
            false_positives=20,
            false_negatives=15,
            total=200,
        )
        assert r.tpr == 0.85
        assert r.tnr == 0.80
        assert r.meets_targets is True

    def test_meets_targets_boundary_fail(self) -> None:
        # TPR = 84/100 = 0.84 -> should fail
        r = CalibrationResult(
            agent="a",
            criterion="c",
            true_positives=84,
            true_negatives=80,
            false_positives=20,
            false_negatives=16,
            total=200,
        )
        assert r.tpr == 0.84
        assert r.meets_targets is False

    def test_zero_denominators(self) -> None:
        r = CalibrationResult(
            agent="a",
            criterion="c",
            true_positives=0,
            true_negatives=0,
            false_positives=0,
            false_negatives=0,
            total=0,
        )
        assert r.tpr == 0.0
        assert r.tnr == 0.0


class TestCalibrate:
    def test_perfect_calibration(self) -> None:
        labels = [
            _label("t1", "scaffolder", "brief_fidelity", True),
            _label("t2", "scaffolder", "brief_fidelity", False),
        ]
        judge_lookup = {
            ("t1", "brief_fidelity"): True,
            ("t2", "brief_fidelity"): False,
        }
        results = calibrate(labels, judge_lookup)
        assert len(results) == 1
        assert results[0].true_positives == 1
        assert results[0].true_negatives == 1
        assert results[0].false_positives == 0
        assert results[0].false_negatives == 0

    def test_mixed_results(self) -> None:
        labels = [
            _label("t1", "scaffolder", "a", True),
            _label("t2", "scaffolder", "a", True),
            _label("t3", "scaffolder", "a", False),
        ]
        judge_lookup = {
            ("t1", "a"): True,  # TP
            ("t2", "a"): False,  # FN
            ("t3", "a"): True,  # FP
        }
        results = calibrate(labels, judge_lookup)
        assert results[0].true_positives == 1
        assert results[0].false_negatives == 1
        assert results[0].false_positives == 1

    def test_skips_missing_verdicts(self) -> None:
        labels = [
            _label("t1", "scaffolder", "a", True),
            _label("t2", "scaffolder", "a", True),  # No judge verdict for t2
        ]
        judge_lookup = {("t1", "a"): True}
        results = calibrate(labels, judge_lookup)
        assert results[0].total == 1

    def test_groups_by_agent_criterion(self) -> None:
        labels = [
            _label("t1", "scaffolder", "a", True),
            _label("t1", "scaffolder", "b", False),
            _label("t2", "dark_mode", "a", True),
        ]
        judge_lookup = {
            ("t1", "a"): True,
            ("t1", "b"): False,
            # No verdict for ("t2", "a") -> dark_mode:a skipped
        }
        results = calibrate(labels, judge_lookup)
        assert len(results) == 2


class TestBuildCalibrationReport:
    def test_all_passing(self) -> None:
        results = [
            CalibrationResult("a", "c1", 9, 1, 0, 0, 10),
            CalibrationResult("a", "c2", 9, 1, 0, 0, 10),
        ]
        report = build_calibration_report(results)
        assert report["all_meet_targets"] is True
        assert report["failing_criteria"] == 0

    def test_some_failing(self) -> None:
        results = [
            CalibrationResult("a", "c1", 9, 1, 0, 0, 10),  # Passes
            CalibrationResult("a", "c2", 1, 1, 8, 0, 10),  # Fails (low TNR)
        ]
        report = build_calibration_report(results)
        assert report["all_meet_targets"] is False
        assert report["failing_criteria"] == 1
        assert len(report["needs_attention"]) == 1
        assert report["needs_attention"][0]["criterion"] == "c2"
