"""Tests for judge correction injection into prompts (Phase 43.2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

import app.ai.agents.evals.judges.base as base_mod
from app.ai.agents.evals.judges.base import (
    _CORRECTIONS_TOKEN_BUDGET,
    _load_corrections_cached,
    build_system_prompt,
    format_corrections_section,
    set_corrections_enabled,
)
from app.ai.agents.evals.judges.scaffolder import ScaffolderJudge
from app.ai.agents.evals.judges.schemas import JudgeInput


@pytest.fixture(autouse=True)
def _reset_corrections_state() -> None:
    """Clear cache and re-enable corrections between tests."""
    _load_corrections_cached.cache_clear()
    set_corrections_enabled(True)


def _make_correction(
    criterion: str = "brief_fidelity",
    error_type: str = "false_positive",
    trace_id: str = "scaff-001",
    reasoning: str = "The output includes a hero section",
) -> dict[str, str]:
    said = "PASS" if error_type == "false_positive" else "FAIL"
    correct = "FAIL" if error_type == "false_positive" else "PASS"
    return {
        "criterion": criterion,
        "type": error_type,
        "trace_id": trace_id,
        "judge_said": said,
        "correct_answer": correct,
        "judge_reasoning": reasoning,
        "pattern": f"Judge incorrectly said {said}. Reasoning was: {reasoning[:120]}",
    }


def _write_corrections(
    corr_dir: Path,
    agent: str,
    corrections: list[dict[str, str]],
) -> Path:
    """Write a correction YAML file to the given directory."""
    data = {
        "agent": agent,
        "generated": "2026-04-01T00:00:00+00:00",
        "correction_count": len(corrections),
        "corrections": corrections,
    }
    path = corr_dir / f"{agent}_judge_corrections.yaml"
    with path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    return path


def _make_judge_input(agent: str = "scaffolder") -> JudgeInput:
    return JudgeInput(
        trace_id="test-corr-001",
        agent=agent,
        input_data={"brief": "Build a promotional email"},
        output_data={"html": "<table><tr><td>Hello</td></tr></table>"},
        expected_challenges=[],
    )


class TestFormatCorrectionsSection:
    def test_with_yaml_file(self, tmp_path: Any, monkeypatch: Any) -> None:
        """Corrections section includes criterion, trace_id, and header."""
        _write_corrections(
            tmp_path,
            "scaffolder",
            [_make_correction()],
        )
        monkeypatch.setattr(base_mod, "_CORRECTIONS_DIR", tmp_path)

        result = format_corrections_section("scaffolder")

        assert "CORRECTION EXAMPLES" in result
        assert "brief_fidelity" in result
        assert "scaff-001" in result
        assert "You said: PASS" in result
        assert "Correct answer: FAIL" in result

    def test_missing_file_returns_empty(self) -> None:
        """No corrections YAML → empty string."""
        result = format_corrections_section("nonexistent_agent_xyz")
        assert result == ""

    def test_empty_corrections_returns_empty(self, tmp_path: Any, monkeypatch: Any) -> None:
        """YAML with empty corrections list → empty string."""
        _write_corrections(tmp_path, "scaffolder", [])
        monkeypatch.setattr(base_mod, "_CORRECTIONS_DIR", tmp_path)

        result = format_corrections_section("scaffolder")
        assert result == ""

    def test_disabled_flag_returns_empty(self, tmp_path: Any, monkeypatch: Any) -> None:
        """Corrections disabled → empty string even if YAML exists."""
        _write_corrections(tmp_path, "scaffolder", [_make_correction()])
        monkeypatch.setattr(base_mod, "_CORRECTIONS_DIR", tmp_path)

        set_corrections_enabled(False)
        result = format_corrections_section("scaffolder")
        assert result == ""


class TestTokenBudget:
    def test_budget_respected(self, tmp_path: Any, monkeypatch: Any) -> None:
        """Correction section stays within token budget even with many corrections."""
        corrections = [
            _make_correction(
                criterion=f"criterion_{i}",
                trace_id=f"trace-{i:03d}",
                reasoning="x" * 500,
            )
            for i in range(15)
        ]
        _write_corrections(tmp_path, "scaffolder", corrections)
        monkeypatch.setattr(base_mod, "_CORRECTIONS_DIR", tmp_path)

        result = format_corrections_section("scaffolder")
        char_budget = _CORRECTIONS_TOKEN_BUDGET * 4
        assert len(result) <= char_budget + 200  # header overhead


class TestFalsePositivePriority:
    def test_fp_before_fn(self, tmp_path: Any, monkeypatch: Any) -> None:
        """False positive corrections appear before false negatives."""
        corrections = [
            _make_correction(criterion="fn_first", error_type="false_negative", trace_id="fn-001"),
            _make_correction(criterion="fn_second", error_type="false_negative", trace_id="fn-002"),
            _make_correction(criterion="fp_first", error_type="false_positive", trace_id="fp-001"),
        ]
        _write_corrections(tmp_path, "scaffolder", corrections)
        monkeypatch.setattr(base_mod, "_CORRECTIONS_DIR", tmp_path)

        result = format_corrections_section("scaffolder")
        fp_pos = result.index("fp_first")
        fn_pos = result.index("fn_first")
        assert fp_pos < fn_pos


class TestBuildSystemPrompt:
    def test_includes_criteria(self) -> None:
        """System prompt includes the criteria block."""
        from app.ai.agents.evals.judges.scaffolder import SCAFFOLDER_CRITERIA

        result = build_system_prompt(SCAFFOLDER_CRITERIA, "scaffolder")
        assert "brief_fidelity" in result
        assert "email_layout_patterns" in result
        assert "CRITERIA:" in result
        assert "IMPORTANT:" in result

    def test_includes_corrections_when_yaml_exists(self, tmp_path: Any, monkeypatch: Any) -> None:
        """System prompt includes correction section when YAML exists."""
        from app.ai.agents.evals.judges.scaffolder import SCAFFOLDER_CRITERIA

        _write_corrections(tmp_path, "scaffolder", [_make_correction()])
        monkeypatch.setattr(base_mod, "_CORRECTIONS_DIR", tmp_path)

        result = build_system_prompt(SCAFFOLDER_CRITERIA, "scaffolder")
        assert "CORRECTION EXAMPLES" in result
        assert "brief_fidelity" in result


class TestScaffolderJudgeIntegration:
    def test_prompt_includes_corrections(self, tmp_path: Any, monkeypatch: Any) -> None:
        """Full ScaffolderJudge.build_prompt() includes corrections when available."""
        _write_corrections(tmp_path, "scaffolder", [_make_correction()])
        monkeypatch.setattr(base_mod, "_CORRECTIONS_DIR", tmp_path)

        judge = ScaffolderJudge()
        prompt = judge.build_prompt(_make_judge_input())

        assert "CORRECTION EXAMPLES" in prompt
        assert "brief_fidelity" in prompt
        assert "AGENT OUTPUT" in prompt
