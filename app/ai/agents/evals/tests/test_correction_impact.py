"""Tests for correction impact A/B comparison report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.ai.agents.evals.correction_impact import (
    build_impact_report,
    classify_impact,
    load_calibration_pair,
)


def _m(tpr: float, tnr: float) -> dict[str, float]:
    """Shorthand for a metrics dict."""
    return {"tpr": tpr, "tnr": tnr}


def _write_calibration(traces_dir: Path, agent: str, details: list[dict[str, Any]]) -> None:
    """Write a fake *_calibration.json file into *traces_dir*."""
    report = {"agent": agent, "details": details}
    path = traces_dir / f"{agent}_calibration.json"
    path.write_text(json.dumps(report))


# ---------------------------------------------------------------------------
# classify_impact
# ---------------------------------------------------------------------------


class TestClassifyImpact:
    def test_improved_tpr_up(self) -> None:
        assert classify_impact(0.09, 0.0) == "improved"

    def test_improved_tnr_up(self) -> None:
        assert classify_impact(0.0, 0.05) == "improved"

    def test_improved_both_up(self) -> None:
        assert classify_impact(0.05, 0.03) == "improved"

    def test_degraded_tpr_down(self) -> None:
        assert classify_impact(-0.04, 0.0, threshold=0.03) == "degraded"

    def test_degraded_tnr_down(self) -> None:
        assert classify_impact(0.0, -0.04, threshold=0.03) == "degraded"

    def test_no_change_within_tolerance(self) -> None:
        # Both deltas negative but within threshold → no_change
        assert classify_impact(-0.02, -0.01, threshold=0.03) == "no_change"

    def test_no_change_zero_delta(self) -> None:
        assert classify_impact(0.0, 0.0) == "no_change"


# ---------------------------------------------------------------------------
# build_impact_report
# ---------------------------------------------------------------------------


class TestBuildImpactReport:
    def test_all_improved(self) -> None:
        with_m = {"s:a": _m(0.92, 0.87), "s:b": _m(0.90, 0.85)}
        without_m = {"s:a": _m(0.82, 0.78), "s:b": _m(0.85, 0.80)}
        report = build_impact_report(with_m, without_m)

        assert report["_summary"]["criteria_improved"] == 2
        assert report["_summary"]["criteria_degraded"] == 0
        assert report["_summary"]["overall_recommendation"] == "accept"
        assert report["s:a"]["verdict"] == "improved"
        assert report["s:b"]["verdict"] == "improved"

    def test_mixed_verdicts(self) -> None:
        with_m = {"s:a": _m(0.92, 0.87), "s:b": _m(0.85, 0.80)}
        without_m = {"s:a": _m(0.82, 0.78), "s:b": _m(0.85, 0.80)}
        report = build_impact_report(with_m, without_m)

        assert report["_summary"]["criteria_improved"] == 1
        assert report["_summary"]["criteria_unchanged"] == 1
        assert report["_summary"]["overall_recommendation"] == "accept"

    def test_degradation_triggers_review(self) -> None:
        with_m = {"s:a": _m(0.75, 0.70)}
        without_m = {"s:a": _m(0.82, 0.78)}
        report = build_impact_report(with_m, without_m, threshold=0.03)

        assert report["s:a"]["verdict"] == "degraded"
        assert report["_summary"]["criteria_degraded"] == 1
        assert report["_summary"]["overall_recommendation"] == "review"

    def test_empty_metrics(self) -> None:
        report = build_impact_report({}, {})
        assert report["_summary"]["criteria_improved"] == 0
        assert report["_summary"]["criteria_degraded"] == 0
        assert report["_summary"]["criteria_unchanged"] == 0

    def test_delta_values_correct(self) -> None:
        with_m = {"s:a": _m(0.91, 0.85)}
        without_m = {"s:a": _m(0.82, 0.78)}
        report = build_impact_report(with_m, without_m)

        assert report["s:a"]["tpr_delta"] == 0.09
        assert report["s:a"]["tnr_delta"] == 0.07
        assert report["s:a"]["tpr_without"] == 0.82
        assert report["s:a"]["tpr_with"] == 0.91


# ---------------------------------------------------------------------------
# load_calibration_pair
# ---------------------------------------------------------------------------


class TestLoadCalibrationPair:
    def test_loads_from_two_dirs(self, tmp_path: Path) -> None:
        with_dir = tmp_path / "with"
        without_dir = tmp_path / "without"
        with_dir.mkdir()
        without_dir.mkdir()

        _write_calibration(
            with_dir,
            "scaffolder",
            [{"agent": "scaffolder", "criterion": "brief_fidelity", "tpr": 0.91, "tnr": 0.85}],
        )
        _write_calibration(
            without_dir,
            "scaffolder",
            [{"agent": "scaffolder", "criterion": "brief_fidelity", "tpr": 0.82, "tnr": 0.78}],
        )

        with_metrics, without_metrics = load_calibration_pair(with_dir, without_dir)

        assert "scaffolder:brief_fidelity" in with_metrics
        assert with_metrics["scaffolder:brief_fidelity"]["tpr"] == 0.91
        assert without_metrics["scaffolder:brief_fidelity"]["tpr"] == 0.82

    def test_handles_empty_dirs(self, tmp_path: Path) -> None:
        with_dir = tmp_path / "with"
        without_dir = tmp_path / "without"
        with_dir.mkdir()
        without_dir.mkdir()

        with_metrics, without_metrics = load_calibration_pair(with_dir, without_dir)
        assert with_metrics == {}
        assert without_metrics == {}


# ---------------------------------------------------------------------------
# CLI main
# ---------------------------------------------------------------------------


class TestMain:
    def test_writes_report_json(self, tmp_path: Path) -> None:
        with_dir = tmp_path / "with"
        without_dir = tmp_path / "without"
        with_dir.mkdir()
        without_dir.mkdir()
        output = tmp_path / "report.json"

        _write_calibration(
            with_dir,
            "scaffolder",
            [{"agent": "scaffolder", "criterion": "brief_fidelity", "tpr": 0.91, "tnr": 0.85}],
        )
        _write_calibration(
            without_dir,
            "scaffolder",
            [{"agent": "scaffolder", "criterion": "brief_fidelity", "tpr": 0.82, "tnr": 0.78}],
        )

        import sys

        from app.ai.agents.evals.correction_impact import main

        sys.argv = [
            "correction_impact",
            "--with-corrections",
            str(with_dir),
            "--without-corrections",
            str(without_dir),
            "--output",
            str(output),
        ]
        main()

        assert output.exists()
        data = json.loads(output.read_text())
        assert "scaffolder:brief_fidelity" in data
        assert data["_summary"]["overall_recommendation"] == "accept"

    def test_exits_1_on_degradation(self, tmp_path: Path) -> None:
        with_dir = tmp_path / "with"
        without_dir = tmp_path / "without"
        with_dir.mkdir()
        without_dir.mkdir()
        output = tmp_path / "report.json"

        _write_calibration(
            with_dir,
            "scaffolder",
            [{"agent": "scaffolder", "criterion": "brief_fidelity", "tpr": 0.70, "tnr": 0.65}],
        )
        _write_calibration(
            without_dir,
            "scaffolder",
            [{"agent": "scaffolder", "criterion": "brief_fidelity", "tpr": 0.90, "tnr": 0.85}],
        )

        import sys

        import pytest

        from app.ai.agents.evals.correction_impact import main

        sys.argv = [
            "correction_impact",
            "--with-corrections",
            str(with_dir),
            "--without-corrections",
            str(without_dir),
            "--output",
            str(output),
        ]
        with pytest.raises(SystemExit, match="1"):
            main()
