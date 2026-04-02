"""Tests for calibration knowledge document generator (scripts/generate-calibration-knowledge.py)."""

from __future__ import annotations

# Import from the script — it's not a package, so use importlib
import importlib.util
import json
from pathlib import Path
from typing import Any

_spec = importlib.util.spec_from_file_location(
    "generate_calibration_knowledge",
    Path(__file__).resolve().parents[5] / "scripts" / "generate-calibration-knowledge.py",
)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# Re-export functions under a convenient alias
mod = _mod


def _make_detail(
    agent: str,
    criterion: str,
    *,
    tpr: float = 0.95,
    tnr: float = 0.90,
    meets: bool = True,
    tp: int = 19,
    tn: int = 18,
    fp: int = 2,
    fn: int = 1,
) -> dict[str, Any]:
    return {
        "agent": agent,
        "criterion": criterion,
        "tpr": tpr,
        "tnr": tnr,
        "meets_targets": meets,
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "total_labels": tp + tn + fp + fn,
    }


def _make_calibration(
    details: list[dict[str, Any]],
    needs_attention: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "all_meet_targets": len(needs_attention or []) == 0,
        "total_criteria": len(details),
        "passing_criteria": sum(1 for d in details if d["meets_targets"]),
        "failing_criteria": sum(1 for d in details if not d["meets_targets"]),
        "target_tpr": 0.85,
        "target_tnr": 0.80,
        "details": details,
        "needs_attention": needs_attention or [],
    }


def _write_calibration(path: Path, cal: dict[str, Any]) -> None:
    path.write_text(json.dumps(cal, indent=2))


class TestLoadAllCalibrations:
    def test_reads_all_files(self, tmp_path: Path) -> None:
        _write_calibration(
            tmp_path / "scaffolder_calibration.json",
            _make_calibration([_make_detail("scaffolder", "brief_fidelity")]),
        )
        _write_calibration(
            tmp_path / "dark_mode_calibration.json",
            _make_calibration([_make_detail("dark_mode", "color_coherence")]),
        )
        result = mod.load_all_calibrations(tmp_path)
        assert len(result) == 2

    def test_skips_malformed(self, tmp_path: Path) -> None:
        _write_calibration(
            tmp_path / "scaffolder_calibration.json",
            _make_calibration([_make_detail("scaffolder", "brief_fidelity")]),
        )
        (tmp_path / "broken_calibration.json").write_text("{bad json")
        result = mod.load_all_calibrations(tmp_path)
        assert len(result) == 1


class TestExtractCrossAgentPatterns:
    def test_finds_shared_failures(self) -> None:
        details = [
            _make_detail("scaffolder", "html_preservation", meets=False, tpr=0.70, tnr=0.60),
            _make_detail("dark_mode", "html_preservation", meets=False, tpr=0.75, tnr=0.65),
        ]
        patterns = mod.extract_cross_agent_patterns(details)
        assert len(patterns) == 1
        assert patterns[0]["criterion"] == "html_preservation"
        assert sorted(patterns[0]["agents"]) == ["dark_mode", "scaffolder"]
        assert patterns[0]["avg_tpr"] == round((0.70 + 0.75) / 2, 4)

    def test_ignores_single_agent(self) -> None:
        details = [
            _make_detail("scaffolder", "html_preservation", meets=False, tpr=0.70, tnr=0.60),
            _make_detail("dark_mode", "color_coherence", meets=False, tpr=0.75, tnr=0.65),
        ]
        patterns = mod.extract_cross_agent_patterns(details)
        assert len(patterns) == 0


class TestExtractEarlyWarnings:
    def test_flags_approaching_threshold(self) -> None:
        details = [
            _make_detail("scaffolder", "brief_fidelity", tpr=0.88, tnr=0.90, meets=True),
        ]
        warnings = mod.extract_early_warnings(details)
        assert len(warnings) == 1
        assert warnings[0]["agent"] == "scaffolder"
        assert "TPR" in warnings[0]["risk"]

    def test_skips_healthy_criteria(self) -> None:
        details = [
            _make_detail("scaffolder", "brief_fidelity", tpr=0.95, tnr=0.92, meets=True),
        ]
        warnings = mod.extract_early_warnings(details)
        assert len(warnings) == 0

    def test_skips_failing_criteria(self) -> None:
        details = [
            _make_detail("scaffolder", "brief_fidelity", tpr=0.70, tnr=0.60, meets=False),
        ]
        warnings = mod.extract_early_warnings(details)
        assert len(warnings) == 0


class TestExtractDisagreementExamples:
    def test_capped_at_3(self) -> None:
        verdicts: dict[tuple[str, str, str], tuple[bool, str]] = {}
        labels: dict[tuple[str, str, str], bool] = {}
        for i in range(5):
            key = ("scaffolder", f"t{i}", "brief_fidelity")
            verdicts[key] = (True, f"reasoning {i}")
            labels[key] = False  # human says FAIL -> FP
        examples = mod.extract_disagreement_examples(verdicts, labels)
        assert len(examples[("scaffolder", "brief_fidelity")]) == 3

    def test_detects_fp_and_fn(self) -> None:
        verdicts = {
            ("scaffolder", "t1", "brief"): (True, "ok"),  # judge PASS
            ("scaffolder", "t2", "brief"): (False, "bad"),  # judge FAIL
        }
        labels = {
            ("scaffolder", "t1", "brief"): False,  # human FAIL -> FP
            ("scaffolder", "t2", "brief"): True,  # human PASS -> FN
        }
        examples = mod.extract_disagreement_examples(verdicts, labels)
        items = examples[("scaffolder", "brief")]
        types = {e["error_type"] for e in items}
        assert types == {"false_positive", "false_negative"}


class TestGenerateMarkdown:
    def test_structure(self) -> None:
        cal = _make_calibration(
            [
                _make_detail("scaffolder", "brief_fidelity"),
                _make_detail("dark_mode", "color_coherence"),
            ]
        )
        md = mod.generate_markdown([cal], [], [], {})
        assert "# Judge Calibration Insights" in md
        assert "## Per-Agent Calibration Summary" in md
        assert "## Criteria Approaching Failure Threshold" in md
        assert "## Cross-Agent Patterns" in md
        assert "## Common Disagreement Patterns" in md
        assert "### scaffolder" in md
        assert "### dark_mode" in md
        assert "brief_fidelity" in md
        assert "<" not in md or "Auto-generated" in md  # no raw HTML

    def test_idempotent(self) -> None:
        cal = _make_calibration([_make_detail("scaffolder", "brief_fidelity")])
        md1 = mod.generate_markdown([cal], [], [], {})
        md2 = mod.generate_markdown([cal], [], [], {})
        # Strip timestamp line for comparison
        lines1 = [ln for ln in md1.splitlines() if not ln.startswith("> Auto-generated")]
        lines2 = [ln for ln in md2.splitlines() if not ln.startswith("> Auto-generated")]
        assert lines1 == lines2
