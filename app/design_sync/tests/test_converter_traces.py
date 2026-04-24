"""Tests for converter traces JSONL writer (48.3)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import pytest

from app.design_sync.converter_traces import (
    append_trace,
    build_trace,
    compute_quality_score,
)
from app.design_sync.quality_contracts import QualityWarning


@dataclass(frozen=True)
class _FakeCompatHint:
    level: str = "warning"
    message: str = "test"


@dataclass(frozen=True)
class _FakeConversionResult:
    html: str = "<table></table>"
    sections_count: int = 5
    warnings: list[str] = field(default_factory=list[str])
    quality_warnings: list[QualityWarning] = field(default_factory=list[QualityWarning])
    match_confidences: dict[int, float] = field(default_factory=dict[int, float])
    compatibility_hints: list[_FakeCompatHint] = field(default_factory=list[_FakeCompatHint])
    figma_url: str | None = None
    node_id: str | None = None
    design_tokens_used: dict[str, object] | None = None
    cache_hit_rate: float | None = None


def _make_warning(
    category: Literal["contrast", "completeness", "placeholder", "image_bgcolor"] = "contrast",
    severity: Literal["error", "warning", "info"] = "warning",
    message: str = "Low contrast",
) -> QualityWarning:
    return QualityWarning(category=category, severity=severity, message=message)


class TestBuildTrace:
    def test_complete(self) -> None:
        result = _FakeConversionResult(
            quality_warnings=[_make_warning()],
            match_confidences={0: 0.9, 1: 0.5},
            compatibility_hints=[_FakeCompatHint()],
            figma_url="https://figma.com/file/abc",
            node_id="2833:1623",
            cache_hit_rate=0.85,
            design_tokens_used={"primary_color": "#1a1a1a"},
        )
        trace = build_trace(result, "42")  # type: ignore[arg-type]

        assert trace["trace_id"].startswith("conv-42-")
        assert trace["connection_id"] == "42"
        assert trace["figma_url"] == "https://figma.com/file/abc"
        assert trace["node_id"] == "2833:1623"
        assert trace["sections_count"] == 5
        assert len(trace["warnings"]) == 1
        assert trace["warnings"][0]["category"] == "contrast"
        assert trace["match_confidences"] == {"0": 0.9, "1": 0.5}
        assert isinstance(trace["avg_confidence"], float)
        assert isinstance(trace["min_confidence"], float)
        assert isinstance(trace["quality_score"], float)
        assert trace["compatibility_hint_count"] == 1
        assert trace["cache_hit_rate"] == 0.85
        assert trace["timestamp"]

    def test_minimal(self) -> None:
        result = _FakeConversionResult()
        trace = build_trace(result, None)  # type: ignore[arg-type]
        assert trace["trace_id"].startswith("conv-none-")
        assert trace["warnings"] == []
        assert trace["match_confidences"] == {}
        assert trace["avg_confidence"] == 1.0
        assert trace["min_confidence"] == 1.0


class TestComputeQualityScore:
    def test_perfect(self) -> None:
        result = _FakeConversionResult(
            quality_warnings=[],
            match_confidences={0: 1.0, 1: 1.0},
        )
        assert compute_quality_score(result) == pytest.approx(1.0)  # type: ignore[arg-type]

    def test_degraded(self) -> None:
        result = _FakeConversionResult(
            quality_warnings=[
                _make_warning("contrast", "error", "Bad"),
                _make_warning("completeness", "warning", "Missing"),
            ],
            match_confidences={0: 0.5, 1: 0.3},
            sections_count=2,
        )
        score = compute_quality_score(result)  # type: ignore[arg-type]
        assert 0.0 < score < 0.7


class TestAppendTrace:
    def test_creates_file(self, tmp_path: Path) -> None:
        trace_file = tmp_path / "traces" / "test.jsonl"
        trace = {"trace_id": "test-1", "quality_score": 0.8}
        append_trace(trace, trace_file)
        assert trace_file.exists()
        lines = trace_file.read_text().strip().split("\n")
        assert len(lines) == 1
        assert json.loads(lines[0])["trace_id"] == "test-1"

    def test_appends(self, tmp_path: Path) -> None:
        trace_file = tmp_path / "test.jsonl"
        append_trace({"trace_id": "t1"}, trace_file)
        append_trace({"trace_id": "t2"}, trace_file)
        lines = trace_file.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[1])["trace_id"] == "t2"
