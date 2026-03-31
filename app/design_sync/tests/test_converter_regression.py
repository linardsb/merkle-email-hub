"""Tests for converter regression detection (48.3)."""

from __future__ import annotations

import json
from pathlib import Path

from app.design_sync.converter_regression import (
    compute_aggregate_metrics,
    detect_regressions,
    load_baseline,
    load_traces,
    save_baseline,
)


def _make_trace(
    quality_score: float = 0.8,
    avg_confidence: float = 0.85,
    sections_count: int = 5,
    warnings: list[dict[str, str]] | None = None,
    match_confidences: dict[str, float] | None = None,
) -> dict[str, object]:
    return {
        "trace_id": "conv-test-abc",
        "quality_score": quality_score,
        "avg_confidence": avg_confidence,
        "sections_count": sections_count,
        "warnings": warnings or [],
        "match_confidences": match_confidences or {"0": 0.9, "1": 0.8},
    }


class TestLoadTraces:
    def test_loads_recent(self, tmp_path: Path) -> None:
        trace_file = tmp_path / "traces.jsonl"
        traces = [_make_trace(quality_score=0.7 + i * 0.01) for i in range(5)]
        trace_file.write_text("\n".join(json.dumps(t) for t in traces))
        loaded = load_traces(trace_file, last_n=3)
        assert len(loaded) == 3
        assert loaded[0]["quality_score"] == 0.72

    def test_missing_file(self, tmp_path: Path) -> None:
        assert load_traces(tmp_path / "missing.jsonl") == []


class TestComputeAggregateMetrics:
    def test_correct_averages(self) -> None:
        traces = [
            _make_trace(quality_score=0.8, avg_confidence=0.9),
            _make_trace(quality_score=0.6, avg_confidence=0.7),
        ]
        metrics = compute_aggregate_metrics(traces)  # type: ignore[arg-type]
        assert abs(metrics["avg_quality_score"] - 0.7) < 0.01
        assert abs(metrics["avg_confidence"] - 0.8) < 0.01

    def test_empty(self) -> None:
        metrics = compute_aggregate_metrics([])
        assert all(v == 0.0 for v in metrics.values())


class TestDetectRegressions:
    def test_none_within_tolerance(self) -> None:
        baseline = {"avg_quality_score": 0.8, "avg_confidence": 0.85}
        current = {"avg_quality_score": 0.78, "avg_confidence": 0.83}
        assert detect_regressions(current, baseline, tolerance=0.05) == []

    def test_found(self) -> None:
        baseline = {"avg_quality_score": 0.8, "avg_confidence": 0.85}
        current = {"avg_quality_score": 0.70, "avg_confidence": 0.85}
        regressed = detect_regressions(current, baseline, tolerance=0.05)
        assert "avg_quality_score" in regressed


class TestBaselineRoundTrip:
    def test_save_load(self, tmp_path: Path) -> None:
        baseline_path = tmp_path / "baseline.json"
        metrics = {"avg_quality_score": 0.82, "avg_confidence": 0.88}
        save_baseline(metrics, baseline_path)
        loaded = load_baseline(baseline_path)
        assert loaded == metrics

    def test_missing_returns_none(self, tmp_path: Path) -> None:
        assert load_baseline(tmp_path / "missing.json") is None
