"""Tests for scripts/eval-compare-verdicts.py."""

from __future__ import annotations

# Import from the script — it's not a package, so use importlib
import importlib.util
import json
from pathlib import Path
from typing import Any

_spec = importlib.util.spec_from_file_location(
    "eval_compare_verdicts",
    Path(__file__).resolve().parents[5] / "scripts" / "eval-compare-verdicts.py",
)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

load_verdicts = _mod.load_verdicts
extract_criterion_verdicts = _mod.extract_criterion_verdicts
compare_verdicts = _mod.compare_verdicts
build_report = _mod.build_report
main = _mod.main


def _write_verdicts(path: Path, verdicts: list[dict[str, Any]]) -> None:
    """Write verdict dicts as JSONL."""
    with path.open("w") as f:
        for v in verdicts:
            f.write(json.dumps(v) + "\n")


def _make_verdict(
    trace_id: str,
    agent: str,
    criteria: dict[str, bool],
) -> dict[str, Any]:
    """Build a verdict dict from criterion name → passed mapping."""
    return {
        "trace_id": trace_id,
        "agent": agent,
        "overall_pass": all(criteria.values()),
        "criteria_results": [
            {"criterion": c, "passed": p, "reasoning": f"{'Pass' if p else 'Fail'}: {c}"}
            for c, p in criteria.items()
        ],
        "error": None,
    }


class TestLoadVerdicts:
    def test_loads_jsonl(self, tmp_path: Path) -> None:
        path = tmp_path / "test_verdicts.jsonl"
        v = _make_verdict("t1", "scaffolder", {"c1": True})
        _write_verdicts(path, [v])
        result = load_verdicts(path)
        assert len(result) == 1
        assert result[0]["trace_id"] == "t1"

    def test_missing_file(self, tmp_path: Path) -> None:
        result = load_verdicts(tmp_path / "missing.jsonl")
        assert result == []


class TestExtractCriterionVerdicts:
    def test_flattens_criteria(self) -> None:
        v = _make_verdict("t1", "scaffolder", {"c1": True, "c2": False})
        result = extract_criterion_verdicts([v])
        assert result[("t1", "c1")] is True
        assert result[("t1", "c2")] is False


class TestCompareVerdicts:
    def test_no_flips(self, tmp_path: Path) -> None:
        """Identical pre/post → flip_rate=0.0."""
        pre = tmp_path / "pre"
        post = tmp_path / "post"
        pre.mkdir()
        post.mkdir()

        verdicts = [
            _make_verdict("t1", "scaffolder", {"c1": True, "c2": False}),
            _make_verdict("t2", "scaffolder", {"c1": True, "c2": True}),
        ]
        _write_verdicts(pre / "scaffolder_verdicts.jsonl", verdicts)
        _write_verdicts(post / "scaffolder_verdicts.jsonl", verdicts)

        results = compare_verdicts(pre, post)
        for r in results.values():
            assert r["flips"] == 0
            assert r["flip_rate"] == 0.0

    def test_all_flips(self, tmp_path: Path) -> None:
        """Every verdict flipped → flip_rate=1.0."""
        pre = tmp_path / "pre"
        post = tmp_path / "post"
        pre.mkdir()
        post.mkdir()

        pre_verdicts = [_make_verdict("t1", "scaffolder", {"c1": True})]
        post_verdicts = [_make_verdict("t1", "scaffolder", {"c1": False})]
        _write_verdicts(pre / "scaffolder_verdicts.jsonl", pre_verdicts)
        _write_verdicts(post / "scaffolder_verdicts.jsonl", post_verdicts)

        results = compare_verdicts(pre, post)
        assert results["scaffolder:c1"]["flip_rate"] == 1.0
        assert results["scaffolder:c1"]["pass_to_fail"] == 1
        assert results["scaffolder:c1"]["fail_to_pass"] == 0

    def test_partial_flips(self, tmp_path: Path) -> None:
        """Mix of flipped and stable → correct counts."""
        pre = tmp_path / "pre"
        post = tmp_path / "post"
        pre.mkdir()
        post.mkdir()

        pre_verdicts = [
            _make_verdict("t1", "scaffolder", {"c1": True}),
            _make_verdict("t2", "scaffolder", {"c1": False}),
            _make_verdict("t3", "scaffolder", {"c1": True}),
        ]
        post_verdicts = [
            _make_verdict("t1", "scaffolder", {"c1": False}),  # flip: pass→fail
            _make_verdict("t2", "scaffolder", {"c1": True}),  # flip: fail→pass
            _make_verdict("t3", "scaffolder", {"c1": True}),  # stable
        ]
        _write_verdicts(pre / "scaffolder_verdicts.jsonl", pre_verdicts)
        _write_verdicts(post / "scaffolder_verdicts.jsonl", post_verdicts)

        results = compare_verdicts(pre, post)
        r = results["scaffolder:c1"]
        assert r["total"] == 3
        assert r["flips"] == 2
        assert r["pass_to_fail"] == 1
        assert r["fail_to_pass"] == 1
        assert abs(r["flip_rate"] - 2 / 3) < 0.001

    def test_missing_post_trace(self, tmp_path: Path) -> None:
        """Trace in pre but not post → excluded from comparison."""
        pre = tmp_path / "pre"
        post = tmp_path / "post"
        pre.mkdir()
        post.mkdir()

        pre_verdicts = [
            _make_verdict("t1", "scaffolder", {"c1": True}),
            _make_verdict("t2", "scaffolder", {"c1": True}),
        ]
        post_verdicts = [
            _make_verdict("t1", "scaffolder", {"c1": True}),
            # t2 missing
        ]
        _write_verdicts(pre / "scaffolder_verdicts.jsonl", pre_verdicts)
        _write_verdicts(post / "scaffolder_verdicts.jsonl", post_verdicts)

        results = compare_verdicts(pre, post)
        assert results["scaffolder:c1"]["total"] == 1

    def test_empty_files(self, tmp_path: Path) -> None:
        """Empty JSONL files → no results."""
        pre = tmp_path / "pre"
        post = tmp_path / "post"
        pre.mkdir()
        post.mkdir()

        (pre / "scaffolder_verdicts.jsonl").write_text("")
        (post / "scaffolder_verdicts.jsonl").write_text("")

        results = compare_verdicts(pre, post)
        assert results == {}

    def test_multiple_agents(self, tmp_path: Path) -> None:
        """Aggregates across scaffolder + dark_mode files."""
        pre = tmp_path / "pre"
        post = tmp_path / "post"
        pre.mkdir()
        post.mkdir()

        scaff_pre = [_make_verdict("s1", "scaffolder", {"c1": True})]
        scaff_post = [_make_verdict("s1", "scaffolder", {"c1": False})]
        dm_pre = [_make_verdict("d1", "dark_mode", {"color": True})]
        dm_post = [_make_verdict("d1", "dark_mode", {"color": True})]

        _write_verdicts(pre / "scaffolder_verdicts.jsonl", scaff_pre)
        _write_verdicts(post / "scaffolder_verdicts.jsonl", scaff_post)
        _write_verdicts(pre / "dark_mode_verdicts.jsonl", dm_pre)
        _write_verdicts(post / "dark_mode_verdicts.jsonl", dm_post)

        results = compare_verdicts(pre, post)
        assert "scaffolder:c1" in results
        assert "dark_mode:color" in results
        assert results["scaffolder:c1"]["flips"] == 1
        assert results["dark_mode:color"]["flips"] == 0

    def test_missing_pre_agent(self, tmp_path: Path) -> None:
        """Agent in post but not pre → not compared."""
        pre = tmp_path / "pre"
        post = tmp_path / "post"
        pre.mkdir()
        post.mkdir()

        (post / "scaffolder_verdicts.jsonl").write_text(
            json.dumps(_make_verdict("t1", "scaffolder", {"c1": True})) + "\n"
        )

        results = compare_verdicts(pre, post)
        assert results == {}


class TestBuildReport:
    def test_priority_review_threshold(self) -> None:
        """Criteria with flip_rate > threshold appear in priority_review."""
        results = {
            "scaffolder:c1": {
                "agent": "scaffolder",
                "criterion": "c1",
                "total": 10,
                "flips": 3,
                "flip_rate": 0.30,
                "pass_to_fail": 1,
                "fail_to_pass": 2,
                "pre_pass_rate": 0.70,
                "post_pass_rate": 0.80,
            },
            "scaffolder:c2": {
                "agent": "scaffolder",
                "criterion": "c2",
                "total": 10,
                "flips": 1,
                "flip_rate": 0.10,
                "pass_to_fail": 0,
                "fail_to_pass": 1,
                "pre_pass_rate": 0.90,
                "post_pass_rate": 1.0,
            },
        }
        report = build_report(results, threshold=0.20)
        assert report["priority_review"] == ["scaffolder:c1"]
        assert report["summary"]["high_flip_criteria"] == 1
        assert report["summary"]["total_criteria"] == 2

    def test_pass_rate_calculation(self, tmp_path: Path) -> None:
        """Pre/post pass rates computed correctly."""
        pre = tmp_path / "pre"
        post = tmp_path / "post"
        pre.mkdir()
        post.mkdir()

        pre_verdicts = [
            _make_verdict("t1", "scaffolder", {"c1": True}),
            _make_verdict("t2", "scaffolder", {"c1": False}),
            _make_verdict("t3", "scaffolder", {"c1": True}),
            _make_verdict("t4", "scaffolder", {"c1": False}),
        ]
        post_verdicts = [
            _make_verdict("t1", "scaffolder", {"c1": True}),
            _make_verdict("t2", "scaffolder", {"c1": True}),
            _make_verdict("t3", "scaffolder", {"c1": True}),
            _make_verdict("t4", "scaffolder", {"c1": False}),
        ]
        _write_verdicts(pre / "scaffolder_verdicts.jsonl", pre_verdicts)
        _write_verdicts(post / "scaffolder_verdicts.jsonl", post_verdicts)

        results = compare_verdicts(pre, post)
        r = results["scaffolder:c1"]
        assert r["pre_pass_rate"] == 0.5
        assert r["post_pass_rate"] == 0.75


class TestMain:
    def test_cli_output(self, tmp_path: Path) -> None:
        """CLI writes JSON report."""
        pre = tmp_path / "pre"
        post = tmp_path / "post"
        pre.mkdir()
        post.mkdir()
        out = tmp_path / "report.json"

        _write_verdicts(
            pre / "scaffolder_verdicts.jsonl",
            [_make_verdict("t1", "scaffolder", {"c1": True})],
        )
        _write_verdicts(
            post / "scaffolder_verdicts.jsonl",
            [_make_verdict("t1", "scaffolder", {"c1": False})],
        )

        rc = main(["--pre-dir", str(pre), "--post-dir", str(post), "--output", str(out)])
        assert rc == 0
        assert out.exists()
        report = json.loads(out.read_text())
        assert "criteria" in report
        assert "scaffolder:c1" in report["criteria"]

    def test_missing_dir(self, tmp_path: Path) -> None:
        """CLI returns error for missing dir."""
        rc = main(
            [
                "--pre-dir",
                str(tmp_path / "nonexistent"),
                "--post-dir",
                str(tmp_path),
                "--output",
                str(tmp_path / "out.json"),
            ]
        )
        assert rc == 1
