"""Tests for calibration delta tracking and regression gating."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.ai.agents.evals.calibration_tracker import (
    compare_calibration,
    extract_metrics,
    load_baseline,
    save_baseline,
)


def _metrics(agent: str, criterion: str, tpr: float, tnr: float) -> tuple[str, dict[str, float]]:
    """Build a single metric entry for test convenience."""
    return f"{agent}:{criterion}", {"tpr": tpr, "tnr": tnr}


# ---------------------------------------------------------------------------
# extract_metrics
# ---------------------------------------------------------------------------


class TestExtractMetrics:
    def test_extract_from_single_report(self) -> None:
        reports = {
            "scaffolder": {
                "details": [
                    {
                        "agent": "scaffolder",
                        "criterion": "brief_fidelity",
                        "tpr": 0.90,
                        "tnr": 0.85,
                    },
                    {
                        "agent": "scaffolder",
                        "criterion": "mso_correctness",
                        "tpr": 0.88,
                        "tnr": 0.82,
                    },
                ],
            },
        }
        result = extract_metrics(reports)
        assert len(result) == 2
        assert result["scaffolder:brief_fidelity"] == {"tpr": 0.90, "tnr": 0.85}
        assert result["scaffolder:mso_correctness"] == {"tpr": 0.88, "tnr": 0.82}

    def test_extract_handles_empty_details(self) -> None:
        reports: dict[str, dict[str, Any]] = {"scaffolder": {"details": []}}
        result = extract_metrics(reports)
        assert result == {}


# ---------------------------------------------------------------------------
# compare_calibration
# ---------------------------------------------------------------------------


class TestCompareCalibration:
    def test_no_change(self) -> None:
        k, m = _metrics("scaffolder", "brief_fidelity", 0.90, 0.85)
        current = {k: m}
        baseline = {k: m}
        deltas = compare_calibration(current, baseline)
        assert len(deltas) == 1
        assert deltas[0].regressed is False
        assert deltas[0].tpr_delta == 0.0
        assert deltas[0].tnr_delta == 0.0

    def test_improvement_passes(self) -> None:
        k, _ = _metrics("scaffolder", "brief_fidelity", 0.0, 0.0)
        baseline = {k: {"tpr": 0.80, "tnr": 0.75}}
        current = {k: {"tpr": 0.90, "tnr": 0.85}}
        deltas = compare_calibration(current, baseline)
        assert deltas[0].regressed is False
        assert deltas[0].tpr_delta > 0

    def test_tpr_regression_detected(self) -> None:
        k, _ = _metrics("scaffolder", "brief_fidelity", 0.0, 0.0)
        baseline = {k: {"tpr": 0.90, "tnr": 0.85}}
        current = {k: {"tpr": 0.82, "tnr": 0.85}}  # TPR drops 8pp
        deltas = compare_calibration(current, baseline, threshold=0.05)
        assert deltas[0].regressed is True

    def test_tnr_regression_detected(self) -> None:
        k, _ = _metrics("dark_mode", "color_remapping", 0.0, 0.0)
        baseline = {k: {"tpr": 0.90, "tnr": 0.85}}
        current = {k: {"tpr": 0.90, "tnr": 0.79}}  # TNR drops 6pp
        deltas = compare_calibration(current, baseline, threshold=0.05)
        assert deltas[0].regressed is True

    def test_new_criterion_no_regression(self) -> None:
        k, m = _metrics("content", "new_criterion", 0.88, 0.82)
        current = {k: m}
        baseline: dict[str, dict[str, float]] = {}
        deltas = compare_calibration(current, baseline)
        assert deltas[0].regressed is False
        assert deltas[0].agent == "content"
        assert deltas[0].criterion == "new_criterion"


# ---------------------------------------------------------------------------
# baseline I/O
# ---------------------------------------------------------------------------


class TestBaselineIO:
    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "calibration_baseline.json"
        k1, m1 = _metrics("scaffolder", "brief_fidelity", 0.90, 0.85)
        k2, m2 = _metrics("dark_mode", "color_remapping", 0.88, 0.82)
        original = {k1: m1, k2: m2}

        save_baseline(original, path)
        loaded = load_baseline(path)

        assert loaded == original
        # Verify it's valid JSON on disk.
        with path.open() as f:
            raw = json.load(f)
        assert len(raw) == 2
