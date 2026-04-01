"""Tests for judge correction generator module."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from app.ai.agents.evals.judge_corrections import (
    _build_corrections,
    _extract_disagreements,
    _load_verdicts_with_reasoning,
    generate_corrections,
)
from app.ai.agents.evals.schemas import HumanLabel


def _label(
    trace_id: str,
    agent: str,
    criterion: str,
    human_pass: bool,
) -> HumanLabel:
    return HumanLabel(
        trace_id=trace_id,
        agent=agent,
        criterion=criterion,
        human_pass=human_pass,
        notes="",
    )


def _verdict_line(
    trace_id: str,
    agent: str,
    criteria: dict[str, tuple[bool, str]],
    *,
    error: str | None = None,
) -> str:
    return json.dumps(
        {
            "trace_id": trace_id,
            "agent": agent,
            "overall_pass": all(p for p, _ in criteria.values()),
            "criteria_results": [
                {"criterion": c, "passed": p, "reasoning": r} for c, (p, r) in criteria.items()
            ],
            "error": error,
        }
    )


class TestLoadVerdictsWithReasoning:
    def test_basic(self, tmp_path: Path) -> None:
        vf = tmp_path / "verdicts.jsonl"
        vf.write_text(_verdict_line("t1", "scaffolder", {"brief": (True, "Looks good")}) + "\n")
        result = _load_verdicts_with_reasoning(vf)
        assert result[("t1", "brief")] == (True, "Looks good")

    def test_skips_error_lines(self, tmp_path: Path) -> None:
        vf = tmp_path / "verdicts.jsonl"
        lines = [
            _verdict_line("t1", "scaffolder", {"brief": (True, "ok")}),
            _verdict_line("t2", "scaffolder", {"brief": (False, "bad")}, error="timeout"),
        ]
        vf.write_text("\n".join(lines) + "\n")
        result = _load_verdicts_with_reasoning(vf)
        assert ("t1", "brief") in result
        assert ("t2", "brief") not in result


class TestExtractDisagreements:
    def test_fp_detected(self) -> None:
        labels = [_label("t1", "scaffolder", "brief", False)]
        lookup = {("t1", "brief"): (True, "Judge said pass")}
        result = _extract_disagreements(labels, lookup)
        assert len(result) == 1
        assert result[0]["error_type"] == "false_positive"
        assert result[0]["judge_passed"] is True
        assert result[0]["human_passed"] is False

    def test_fn_detected(self) -> None:
        labels = [_label("t1", "scaffolder", "brief", True)]
        lookup = {("t1", "brief"): (False, "Judge said fail")}
        result = _extract_disagreements(labels, lookup)
        assert len(result) == 1
        assert result[0]["error_type"] == "false_negative"

    def test_agreements_excluded(self) -> None:
        labels = [
            _label("t1", "scaffolder", "brief", True),  # TP
            _label("t2", "scaffolder", "brief", False),  # TN
        ]
        lookup = {
            ("t1", "brief"): (True, "correct pass"),
            ("t2", "brief"): (False, "correct fail"),
        }
        result = _extract_disagreements(labels, lookup)
        assert len(result) == 0

    def test_no_matching_verdict(self) -> None:
        labels = [_label("t1", "scaffolder", "brief", True)]
        lookup: dict[tuple[str, str], tuple[bool, str]] = {}
        result = _extract_disagreements(labels, lookup)
        assert len(result) == 0


class TestBuildCorrections:
    def test_caps_at_3_per_criterion(self) -> None:
        disagreements = [
            {
                "trace_id": f"t{i}",
                "criterion": "brief",
                "judge_passed": True,
                "human_passed": False,
                "judge_reasoning": f"reasoning {i}",
                "error_type": "false_positive",
            }
            for i in range(5)
        ]
        result = _build_corrections("scaffolder", disagreements)
        assert result["correction_count"] == 3
        assert len(result["corrections"]) == 3

    def test_sorts_by_reasoning_length(self) -> None:
        disagreements = [
            {
                "trace_id": "t1",
                "criterion": "brief",
                "judge_passed": True,
                "human_passed": False,
                "judge_reasoning": "A very long reasoning that goes on and on with details",
                "error_type": "false_positive",
            },
            {
                "trace_id": "t2",
                "criterion": "brief",
                "judge_passed": True,
                "human_passed": False,
                "judge_reasoning": "Short",
                "error_type": "false_positive",
            },
        ]
        # _extract_disagreements sorts by length, so simulate that
        disagreements.sort(key=lambda d: len(str(d["judge_reasoning"])))
        result = _build_corrections("scaffolder", disagreements)
        # Shorter reasoning should come first
        assert result["corrections"][0]["trace_id"] == "t2"
        assert result["corrections"][1]["trace_id"] == "t1"


class TestGenerateCorrections:
    def test_writes_yaml(self, tmp_path: Path) -> None:
        traces = tmp_path / "traces"
        traces.mkdir()
        output = tmp_path / "output"

        # Write a label file with an FP disagreement
        labels_file = traces / "scaffolder_human_labels.jsonl"
        labels_file.write_text(
            json.dumps(
                {
                    "trace_id": "t1",
                    "agent": "scaffolder",
                    "criterion": "brief_fidelity",
                    "human_pass": False,
                    "notes": "",
                }
            )
            + "\n"
        )

        # Write a verdict file where judge says PASS (creating an FP)
        verdicts_file = traces / "scaffolder_verdicts.jsonl"
        verdicts_file.write_text(
            _verdict_line(
                "t1",
                "scaffolder",
                {"brief_fidelity": (True, "The output matches the brief")},
            )
            + "\n"
        )

        written = generate_corrections(traces, output)
        assert len(written) == 1
        assert written[0].name == "scaffolder_judge_corrections.yaml"

        data = yaml.safe_load(written[0].read_text())
        assert data["agent"] == "scaffolder"
        assert data["correction_count"] == 1
        assert data["corrections"][0]["criterion"] == "brief_fidelity"
        assert data["corrections"][0]["type"] == "false_positive"
        assert data["corrections"][0]["judge_said"] == "PASS"
        assert data["corrections"][0]["correct_answer"] == "FAIL"

    def test_skips_missing_files(self, tmp_path: Path) -> None:
        traces = tmp_path / "traces"
        traces.mkdir()
        output = tmp_path / "output"

        # No label or verdict files — should skip gracefully
        written = generate_corrections(traces, output)
        assert len(written) == 0
