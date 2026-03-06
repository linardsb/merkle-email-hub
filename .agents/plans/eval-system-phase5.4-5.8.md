# Plan: Phase 5.4-5.8 — Eval Execution, Analysis, Calibration & CI

## Context

Phase 5.1-5.3 delivered: 36 synthetic test cases (12 scaffolder + 10 dark_mode + 14 content), eval runner CLI (`runner.py`), judge runner CLI (`judge_runner.py`), and 3 binary LLM judges with 5 criteria each. The infrastructure captures JSONL traces and verdicts but has never been executed end-to-end.

Phase 5.4-5.8 completes the eval loop: run the first batch, analyze failures, calibrate judges against human labels, calibrate QA gate thresholds, build blueprint pipeline evals, and gate CI on regression.

## Dependency Chain

```
5.4 Error Analysis (reads verdict JSONL)
  depends on: traces + verdicts existing (5.3 was "run first batch" — already have runner/judge infra)

5.5 Judge Calibration (compares judge vs human labels)
  depends on: 5.4 (need failure taxonomy to know WHAT to label)

5.6 QA Gate Calibration (compares QA checks vs human labels)
  depends on: 5.5 (reuses human label dataset)

5.7 Blueprint Pipeline Evals (end-to-end multi-agent traces)
  depends on: 5.4 (need per-agent analysis to design pipeline test cases)

5.8 CI Regression Suite (automated gate)
  depends on: 5.5, 5.6, 5.7 (need calibrated thresholds)
```

## Design Decisions

1. **Human labels**: Prefilled JSONL template scaffolded from traces (user fills `human_pass` + `notes`)
2. **Label files**: One file per agent containing both judge criteria and QA check criteria
3. **Blueprint briefs**: 5 test cases (happy path, dark mode recovery, complex retry, vague brief, accessibility)
4. **CI**: Makefile-only for now. **TODO: Add GitHub Actions workflow `.github/workflows/eval.yml` later**

## Files to Create

| File | Purpose |
|------|---------|
| `app/ai/agents/evals/error_analysis.py` | 5.4 — Failure clustering + taxonomy from verdict JSONL |
| `app/ai/agents/evals/schemas.py` | Shared schemas for analysis/calibration (separate from judge schemas) |
| `app/ai/agents/evals/calibration.py` | 5.5 — Judge calibration: TPR/TNR computation against human labels |
| `app/ai/agents/evals/scaffold_labels.py` | 5.5 — Generate prefilled human label templates from traces + verdicts |
| `app/ai/agents/evals/qa_calibration.py` | 5.6 — QA gate calibration: align 10-point checks with human labels |
| `app/ai/agents/evals/blueprint_eval.py` | 5.7 — Blueprint pipeline end-to-end eval runner |
| `app/ai/agents/evals/regression.py` | 5.8 — Regression detection: compare current vs baseline |
| `app/ai/agents/evals/tests/test_error_analysis.py` | Unit tests for error analysis |
| `app/ai/agents/evals/tests/test_calibration.py` | Unit tests for judge calibration |
| `app/ai/agents/evals/tests/test_qa_calibration.py` | Unit tests for QA gate calibration |
| `app/ai/agents/evals/tests/test_blueprint_eval.py` | Unit tests for blueprint eval runner |
| `app/ai/agents/evals/tests/test_regression.py` | Unit tests for regression detection |
| `app/ai/agents/evals/tests/__init__.py` | Package init |

## Files to Modify

| File | Change |
|------|--------|
| `app/ai/agents/evals/__init__.py` | Export new modules |
| `Makefile` | Add `make eval-run`, `make eval-judge`, `make eval-analysis`, `make eval-check` targets |

## Implementation Steps

---

### Step 1: Shared Eval Schemas (`app/ai/agents/evals/schemas.py`)

Create shared data structures for the analysis and calibration pipeline. These are distinct from `judges/schemas.py` which covers judge I/O.

```python
"""Shared schemas for eval analysis and calibration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FailureCluster:
    """A group of related failures sharing a root pattern."""

    cluster_id: str  # e.g., "scaffolder:brief_fidelity:missing_hero"
    agent: str
    criterion: str
    pattern: str  # Human-readable failure pattern description
    trace_ids: list[str] = field(default_factory=list)
    sample_reasonings: list[str] = field(default_factory=list)  # Up to 3 examples
    count: int = 0

    @property
    def frequency(self) -> float:
        """Frequency as fraction of total traces for this agent+criterion."""
        return 0.0  # Computed externally


@dataclass(frozen=True)
class HumanLabel:
    """A single human judgment on one trace+criterion."""

    trace_id: str
    agent: str
    criterion: str
    human_pass: bool
    notes: str = ""


@dataclass(frozen=True)
class CalibrationResult:
    """TPR/TNR metrics for one criterion."""

    agent: str
    criterion: str
    true_positives: int  # Judge=pass, Human=pass
    true_negatives: int  # Judge=fail, Human=fail
    false_positives: int  # Judge=pass, Human=fail
    false_negatives: int  # Judge=fail, Human=pass
    total: int

    @property
    def tpr(self) -> float:
        """True Positive Rate (sensitivity). Target > 0.85."""
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def tnr(self) -> float:
        """True Negative Rate (specificity). Target > 0.80."""
        denom = self.true_negatives + self.false_positives
        return self.true_negatives / denom if denom > 0 else 0.0

    @property
    def meets_targets(self) -> bool:
        return self.tpr >= 0.85 and self.tnr >= 0.80


@dataclass(frozen=True)
class QACalibrationResult:
    """Agreement metrics for one QA check vs human labels."""

    check_name: str
    agreement_rate: float  # % of times QA check agrees with human
    false_pass_rate: float  # QA says pass but human says fail
    false_fail_rate: float  # QA says fail but human says pass
    total: int
    recommended_threshold: float | None = None  # Suggested score threshold adjustment


@dataclass(frozen=True)
class RegressionReport:
    """Comparison of current eval run vs baseline."""

    agent: str
    current_pass_rate: float
    baseline_pass_rate: float
    delta: float  # current - baseline
    regressed_criteria: list[str]  # Criteria where pass rate dropped > threshold
    improved_criteria: list[str]
    is_regression: bool  # True if any criterion regressed beyond tolerance


@dataclass(frozen=True)
class BlueprintEvalTrace:
    """End-to-end blueprint pipeline evaluation trace."""

    run_id: str
    blueprint_name: str
    brief: str
    total_steps: int
    total_retries: int
    qa_passed: bool | None
    final_html_length: int
    total_tokens: int
    elapsed_seconds: float
    node_trace: list[dict[str, object]]  # Per-node: name, status, iteration, duration_ms
    error: str | None = None
```

---

### Step 2: Error Analysis Module (`app/ai/agents/evals/error_analysis.py`) — Task 5.4

This module reads verdict JSONL files and produces a structured failure taxonomy. It runs offline (CLI) after judge verdicts are collected.

```python
"""Error analysis: cluster failures from judge verdicts into a taxonomy.

CLI: python -m app.ai.agents.evals.error_analysis \
       --verdicts traces/scaffolder_verdicts.jsonl \
       --output traces/scaffolder_analysis.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.ai.agents.evals.schemas import FailureCluster


def load_verdicts(path: Path) -> list[dict[str, Any]]:
    """Load verdict JSONL file into list of dicts."""
    verdicts: list[dict[str, Any]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                verdicts.append(json.loads(line))
    return verdicts


def cluster_failures(verdicts: list[dict[str, Any]]) -> list[FailureCluster]:
    """Group failed criteria by agent+criterion, extract patterns.

    Clusters failures by (agent, criterion) pair. Each cluster contains
    all trace IDs that failed that criterion and sample reasonings for
    manual inspection.
    """
    # Group by (agent, criterion)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for verdict in verdicts:
        if verdict.get("error"):
            continue
        agent = verdict["agent"]
        for cr in verdict.get("criteria_results", []):
            if not cr["passed"]:
                groups[(agent, cr["criterion"])].append(
                    {"trace_id": verdict["trace_id"], "reasoning": cr["reasoning"]}
                )

    clusters: list[FailureCluster] = []
    for (agent, criterion), items in sorted(groups.items()):
        cluster_id = f"{agent}:{criterion}"
        trace_ids = [item["trace_id"] for item in items]
        sample_reasonings = [item["reasoning"] for item in items[:3]]

        # Derive pattern from most common reasoning keywords
        pattern = _extract_pattern(sample_reasonings)

        clusters.append(
            FailureCluster(
                cluster_id=cluster_id,
                agent=agent,
                criterion=criterion,
                pattern=pattern,
                trace_ids=trace_ids,
                sample_reasonings=sample_reasonings,
                count=len(items),
            )
        )

    return sorted(clusters, key=lambda c: c.count, reverse=True)


def _extract_pattern(reasonings: list[str]) -> str:
    """Derive a human-readable failure pattern from sample reasonings.

    Simple keyword extraction — not ML-based. Sufficient for 36-case dataset.
    """
    if not reasonings:
        return "unknown"
    # Use first reasoning as representative pattern (small dataset)
    first = reasonings[0]
    # Truncate to reasonable length
    return first[:120] if len(first) > 120 else first


def compute_pass_rates(
    verdicts: list[dict[str, Any]],
) -> dict[str, dict[str, float]]:
    """Compute per-criterion pass rates grouped by agent.

    Returns: {agent: {criterion: pass_rate}}
    """
    counts: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"passed": 0, "total": 0})
    )

    for verdict in verdicts:
        if verdict.get("error"):
            continue
        agent = verdict["agent"]
        for cr in verdict.get("criteria_results", []):
            counts[agent][cr["criterion"]]["total"] += 1
            if cr["passed"]:
                counts[agent][cr["criterion"]]["passed"] += 1

    rates: dict[str, dict[str, float]] = {}
    for agent, criteria in sorted(counts.items()):
        rates[agent] = {}
        for criterion, ct in sorted(criteria.items()):
            rates[agent][criterion] = (
                ct["passed"] / ct["total"] if ct["total"] > 0 else 0.0
            )
    return rates


def build_analysis_report(
    verdicts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build complete error analysis report from verdict data.

    Returns JSON-serializable dict with:
    - summary: total traces, pass/fail/error counts
    - pass_rates: per-agent per-criterion rates
    - failure_clusters: sorted by count desc
    - top_failures: top 3 failure clusters (priority fixes)
    """
    total = len(verdicts)
    errors = sum(1 for v in verdicts if v.get("error"))
    passed = sum(1 for v in verdicts if v.get("overall_pass") and not v.get("error"))
    failed = total - passed - errors

    clusters = cluster_failures(verdicts)
    pass_rates = compute_pass_rates(verdicts)

    return {
        "summary": {
            "total_traces": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "overall_pass_rate": passed / (total - errors) if (total - errors) > 0 else 0.0,
        },
        "pass_rates": pass_rates,
        "failure_clusters": [
            {
                "cluster_id": c.cluster_id,
                "agent": c.agent,
                "criterion": c.criterion,
                "pattern": c.pattern,
                "count": c.count,
                "trace_ids": c.trace_ids,
                "sample_reasonings": c.sample_reasonings,
            }
            for c in clusters
        ],
        "top_failures": [
            {"cluster_id": c.cluster_id, "count": c.count, "pattern": c.pattern}
            for c in clusters[:3]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze eval judge verdicts")
    parser.add_argument("--verdicts", required=True, help="Path to verdicts JSONL (or directory)")
    parser.add_argument("--output", required=True, help="Path to write analysis JSON")
    args = parser.parse_args()

    verdicts_path = Path(args.verdicts)
    output_path = Path(args.output)

    # Load verdicts from single file or all *_verdicts.jsonl in directory
    all_verdicts: list[dict[str, Any]] = []
    if verdicts_path.is_dir():
        for f in sorted(verdicts_path.glob("*_verdicts.jsonl")):
            all_verdicts.extend(load_verdicts(f))
    else:
        all_verdicts = load_verdicts(verdicts_path)

    if not all_verdicts:
        print("No verdicts found.", file=sys.stderr)
        sys.exit(1)

    report = build_analysis_report(all_verdicts)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(report, f, indent=2)

    # Print summary to stdout
    s = report["summary"]
    print(f"\n=== Error Analysis ===")
    print(f"Traces: {s['total_traces']} (passed={s['passed']}, failed={s['failed']}, errors={s['errors']})")
    print(f"Overall pass rate: {s['overall_pass_rate']:.1%}")

    if report["top_failures"]:
        print(f"\nTop failure clusters:")
        for tf in report["top_failures"]:
            print(f"  [{tf['count']}x] {tf['cluster_id']}: {tf['pattern'][:80]}")

    print(f"\nFull report: {output_path}")


if __name__ == "__main__":
    main()
```

---

### Step 2b: Label Scaffolding Script (`app/ai/agents/evals/scaffold_labels.py`) — Task 5.5 prep

Generates prefilled JSONL label templates from traces and verdicts. User only needs to set `human_pass` to true/false.

```python
"""Scaffold human label templates from traces and verdicts.

Generates one JSONL file per agent with prefilled trace_id, agent, criterion fields.
User fills in human_pass (true/false) and optional notes.

Includes both judge criteria (from verdicts) and QA check criteria (from QA_CHECK_NAMES)
in a single file per agent.

CLI: python -m app.ai.agents.evals.scaffold_labels \
       --verdicts traces/scaffolder_verdicts.jsonl \
       --traces traces/scaffolder_traces.jsonl \
       --output traces/scaffolder_human_labels.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


# QA check names to include as additional labeling criteria
QA_CHECK_NAMES: list[str] = [
    "html_validation",
    "css_support",
    "file_size",
    "link_validation",
    "spam_score",
    "dark_mode",
    "accessibility",
    "fallback",
    "image_optimization",
    "brand_compliance",
]


def scaffold_labels(
    verdicts: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    include_qa_criteria: bool = True,
) -> list[dict[str, Any]]:
    """Generate prefilled label rows from verdicts and traces.

    Each row has: trace_id, agent, criterion, judge_pass (for reference),
    human_pass (null — to be filled), notes (empty).
    """
    labels: list[dict[str, Any]] = []
    trace_ids_with_output: set[str] = {
        t["id"] for t in traces if t.get("output")
    }

    for verdict in verdicts:
        if verdict.get("error"):
            continue
        trace_id = verdict["trace_id"]
        if trace_id not in trace_ids_with_output:
            continue
        agent = verdict["agent"]

        # Judge criteria labels
        for cr in verdict.get("criteria_results", []):
            labels.append({
                "trace_id": trace_id,
                "agent": agent,
                "criterion": cr["criterion"],
                "judge_pass": cr["passed"],  # Reference — not used by calibration
                "human_pass": None,  # <-- FILL THIS IN
                "notes": "",
            })

        # QA check criteria labels (for QA gate calibration)
        if include_qa_criteria:
            for check_name in QA_CHECK_NAMES:
                labels.append({
                    "trace_id": trace_id,
                    "agent": agent,
                    "criterion": check_name,
                    "judge_pass": None,  # QA checks don't have judge verdicts
                    "human_pass": None,  # <-- FILL THIS IN
                    "notes": "",
                })

    return labels


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold human label templates")
    parser.add_argument("--verdicts", required=True, help="Path to verdicts JSONL")
    parser.add_argument("--traces", required=True, help="Path to traces JSONL")
    parser.add_argument("--output", required=True, help="Path to write label template JSONL")
    parser.add_argument("--no-qa", action="store_true", help="Exclude QA check criteria")
    args = parser.parse_args()

    verdicts: list[dict[str, Any]] = []
    with Path(args.verdicts).open() as f:
        for line in f:
            line = line.strip()
            if line:
                verdicts.append(json.loads(line))

    traces: list[dict[str, Any]] = []
    with Path(args.traces).open() as f:
        for line in f:
            line = line.strip()
            if line:
                traces.append(json.loads(line))

    if not verdicts:
        print("No verdicts found.", file=sys.stderr)
        sys.exit(1)

    labels = scaffold_labels(verdicts, traces, include_qa_criteria=not args.no_qa)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        for label in labels:
            f.write(json.dumps(label) + "\n")

    judge_count = sum(1 for l in labels if l["judge_pass"] is not None)
    qa_count = len(labels) - judge_count
    print(f"Scaffolded {len(labels)} label rows ({judge_count} judge + {qa_count} QA) -> {output_path}")
    print(f"Edit the file and set human_pass to true/false for each row.")


if __name__ == "__main__":
    main()
```

---

### Step 3: Judge Calibration Module (`app/ai/agents/evals/calibration.py`) — Task 5.5

Compares judge verdicts against human labels to compute TPR/TNR per criterion. Human labels are stored as JSONL with the `HumanLabel` schema.

```python
"""Judge calibration: compute TPR/TNR against human labels.

Human labels format (JSONL):
{"trace_id": "scaff-001", "agent": "scaffolder", "criterion": "brief_fidelity", "human_pass": true, "notes": ""}

CLI: python -m app.ai.agents.evals.calibration \
       --verdicts traces/scaffolder_verdicts.jsonl \
       --labels traces/scaffolder_human_labels.jsonl \
       --output traces/scaffolder_calibration.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.ai.agents.evals.schemas import CalibrationResult, HumanLabel


def load_human_labels(path: Path) -> list[HumanLabel]:
    """Load human labels from JSONL file."""
    labels: list[HumanLabel] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                labels.append(
                    HumanLabel(
                        trace_id=data["trace_id"],
                        agent=data["agent"],
                        criterion=data["criterion"],
                        human_pass=data["human_pass"],
                        notes=data.get("notes", ""),
                    )
                )
    return labels


def load_judge_verdicts(path: Path) -> dict[tuple[str, str], dict[str, bool]]:
    """Load judge verdicts into lookup: (trace_id, criterion) -> passed.

    Returns: {(trace_id, criterion): {"judge_pass": bool}}
    """
    lookup: dict[tuple[str, str], dict[str, bool]] = {}
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            verdict = json.loads(line)
            if verdict.get("error"):
                continue
            trace_id = verdict["trace_id"]
            for cr in verdict.get("criteria_results", []):
                lookup[(trace_id, cr["criterion"])] = {"judge_pass": cr["passed"]}
    return lookup


def calibrate(
    labels: list[HumanLabel],
    judge_lookup: dict[tuple[str, str], dict[str, bool]],
) -> list[CalibrationResult]:
    """Compute TPR/TNR for each (agent, criterion) pair.

    Only includes labels that have matching judge verdicts.
    """
    # Group by (agent, criterion)
    groups: dict[tuple[str, str], list[tuple[bool, bool]]] = defaultdict(list)

    for label in labels:
        key = (label.trace_id, label.criterion)
        judge = judge_lookup.get(key)
        if judge is None:
            continue  # No matching verdict — skip
        groups[(label.agent, label.criterion)].append(
            (judge["judge_pass"], label.human_pass)
        )

    results: list[CalibrationResult] = []
    for (agent, criterion), pairs in sorted(groups.items()):
        tp = sum(1 for jp, hp in pairs if jp and hp)
        tn = sum(1 for jp, hp in pairs if not jp and not hp)
        fp = sum(1 for jp, hp in pairs if jp and not hp)
        fn = sum(1 for jp, hp in pairs if not jp and hp)

        results.append(
            CalibrationResult(
                agent=agent,
                criterion=criterion,
                true_positives=tp,
                true_negatives=tn,
                false_positives=fp,
                false_negatives=fn,
                total=len(pairs),
            )
        )

    return results


def build_calibration_report(results: list[CalibrationResult]) -> dict[str, Any]:
    """Build JSON-serializable calibration report."""
    criteria_details: list[dict[str, Any]] = []
    all_meet_targets = True

    for r in results:
        meets = r.meets_targets
        if not meets:
            all_meet_targets = False
        criteria_details.append(
            {
                "agent": r.agent,
                "criterion": r.criterion,
                "tpr": round(r.tpr, 4),
                "tnr": round(r.tnr, 4),
                "meets_targets": meets,
                "confusion": {
                    "tp": r.true_positives,
                    "tn": r.true_negatives,
                    "fp": r.false_positives,
                    "fn": r.false_negatives,
                },
                "total_labels": r.total,
            }
        )

    failing = [d for d in criteria_details if not d["meets_targets"]]

    return {
        "all_meet_targets": all_meet_targets,
        "total_criteria": len(results),
        "passing_criteria": len(results) - len(failing),
        "failing_criteria": len(failing),
        "target_tpr": 0.85,
        "target_tnr": 0.80,
        "details": criteria_details,
        "needs_attention": [
            {"agent": d["agent"], "criterion": d["criterion"], "tpr": d["tpr"], "tnr": d["tnr"]}
            for d in failing
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate judges against human labels")
    parser.add_argument("--verdicts", required=True, help="Path to verdicts JSONL")
    parser.add_argument("--labels", required=True, help="Path to human labels JSONL")
    parser.add_argument("--output", required=True, help="Path to write calibration JSON")
    args = parser.parse_args()

    judge_lookup = load_judge_verdicts(Path(args.verdicts))
    labels = load_human_labels(Path(args.labels))

    if not labels:
        print("No human labels found.", file=sys.stderr)
        sys.exit(1)

    results = calibrate(labels, judge_lookup)
    report = build_calibration_report(results)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print(f"\n=== Judge Calibration ===")
    print(f"Criteria evaluated: {report['total_criteria']}")
    print(f"Meeting targets (TPR>{report['target_tpr']}, TNR>{report['target_tnr']}): "
          f"{report['passing_criteria']}/{report['total_criteria']}")

    if report["needs_attention"]:
        print(f"\nNeeds attention:")
        for item in report["needs_attention"]:
            print(f"  {item['agent']}:{item['criterion']} — TPR={item['tpr']:.2f}, TNR={item['tnr']:.2f}")

    status = "PASS" if report["all_meet_targets"] else "FAIL"
    print(f"\nCalibration: {status}")
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
```

---

### Step 4: QA Gate Calibration (`app/ai/agents/evals/qa_calibration.py`) — Task 5.6

Runs the 10-point QA gate on agent output HTML from traces, then compares QA pass/fail against human labels to find miscalibrated checks.

```python
"""QA gate calibration: measure 10-point QA checks against human judgments.

Reads agent traces (which contain HTML output), runs QA checks on each,
then compares QA check pass/fail against human labels on the same traces.

CLI: python -m app.ai.agents.evals.qa_calibration \
       --traces traces/scaffolder_traces.jsonl \
       --labels traces/scaffolder_human_labels.jsonl \
       --output traces/qa_calibration.json

Human labels for QA calibration use criterion names matching QA check names:
{"trace_id": "scaff-001", "agent": "scaffolder", "criterion": "dark_mode", "human_pass": true}
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.ai.agents.evals.schemas import HumanLabel, QACalibrationResult


# Map QA check name -> check class import path
QA_CHECK_NAMES: list[str] = [
    "html_validation",
    "css_support",
    "file_size",
    "link_validation",
    "spam_score",
    "dark_mode",
    "accessibility",
    "fallback",
    "image_optimization",
    "brand_compliance",
]


async def run_qa_on_traces(
    traces: list[dict[str, Any]],
) -> dict[str, dict[str, bool]]:
    """Run all 10 QA checks on each trace's HTML output.

    Returns: {trace_id: {check_name: passed}}
    """
    from app.qa_engine.checks import get_all_checks

    checks = get_all_checks()
    results: dict[str, dict[str, bool]] = {}

    for trace in traces:
        trace_id = trace["id"]
        output = trace.get("output")
        if not output:
            continue

        # Extract HTML from output — field name varies by agent
        html = output.get("html", "")
        if not html:
            continue

        check_results: dict[str, bool] = {}
        for check in checks:
            result = await check.run(html)
            check_results[result.check_name] = result.passed

        results[trace_id] = check_results

    return results


def calibrate_qa(
    qa_results: dict[str, dict[str, bool]],
    labels: list[HumanLabel],
) -> list[QACalibrationResult]:
    """Compare QA check results against human labels.

    Only compares labels where criterion name matches a QA check name.
    """
    # Group by check_name
    groups: dict[str, list[tuple[bool, bool]]] = defaultdict(list)

    for label in labels:
        if label.criterion not in QA_CHECK_NAMES:
            continue
        trace_qa = qa_results.get(label.trace_id)
        if trace_qa is None:
            continue
        qa_pass = trace_qa.get(label.criterion)
        if qa_pass is None:
            continue
        groups[label.criterion].append((qa_pass, label.human_pass))

    results: list[QACalibrationResult] = []
    for check_name in QA_CHECK_NAMES:
        pairs = groups.get(check_name, [])
        if not pairs:
            continue

        total = len(pairs)
        agree = sum(1 for qp, hp in pairs if qp == hp)
        false_pass = sum(1 for qp, hp in pairs if qp and not hp)
        false_fail = sum(1 for qp, hp in pairs if not qp and hp)

        results.append(
            QACalibrationResult(
                check_name=check_name,
                agreement_rate=agree / total if total > 0 else 0.0,
                false_pass_rate=false_pass / total if total > 0 else 0.0,
                false_fail_rate=false_fail / total if total > 0 else 0.0,
                total=total,
            )
        )

    return results


def build_qa_report(results: list[QACalibrationResult]) -> dict[str, Any]:
    """Build JSON-serializable QA calibration report."""
    details = [
        {
            "check_name": r.check_name,
            "agreement_rate": round(r.agreement_rate, 4),
            "false_pass_rate": round(r.false_pass_rate, 4),
            "false_fail_rate": round(r.false_fail_rate, 4),
            "total_labels": r.total,
            "recommended_threshold": r.recommended_threshold,
        }
        for r in results
    ]

    avg_agreement = (
        sum(r.agreement_rate for r in results) / len(results) if results else 0.0
    )

    # Flag checks with < 75% agreement as needing attention
    needs_tuning = [d for d in details if d["agreement_rate"] < 0.75]

    return {
        "average_agreement": round(avg_agreement, 4),
        "checks_evaluated": len(results),
        "checks_needing_tuning": len(needs_tuning),
        "details": details,
        "needs_tuning": needs_tuning,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate QA gate against human labels")
    parser.add_argument("--traces", required=True, help="Path to traces JSONL (with HTML output)")
    parser.add_argument("--labels", required=True, help="Path to human labels JSONL")
    parser.add_argument("--output", required=True, help="Path to write QA calibration JSON")
    args = parser.parse_args()

    # Load traces
    traces: list[dict[str, Any]] = []
    with Path(args.traces).open() as f:
        for line in f:
            line = line.strip()
            if line:
                traces.append(json.loads(line))

    labels_path = Path(args.labels)
    labels: list[HumanLabel] = []
    with labels_path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                labels.append(
                    HumanLabel(
                        trace_id=data["trace_id"],
                        agent=data["agent"],
                        criterion=data["criterion"],
                        human_pass=data["human_pass"],
                        notes=data.get("notes", ""),
                    )
                )

    if not traces or not labels:
        print("Need both traces and labels.", file=sys.stderr)
        sys.exit(1)

    # Run QA checks on trace HTML
    qa_results = asyncio.run(run_qa_on_traces(traces))

    results = calibrate_qa(qa_results, labels)
    report = build_qa_report(results)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(report, f, indent=2)

    print(f"\n=== QA Gate Calibration ===")
    print(f"Checks evaluated: {report['checks_evaluated']}")
    print(f"Average agreement: {report['average_agreement']:.1%}")
    if report["needs_tuning"]:
        print(f"\nNeeds tuning ({len(report['needs_tuning'])} checks < 75% agreement):")
        for item in report["needs_tuning"]:
            print(f"  {item['check_name']}: {item['agreement_rate']:.1%} "
                  f"(false_pass={item['false_pass_rate']:.1%}, false_fail={item['false_fail_rate']:.1%})")
    print(f"\nReport: {args.output}")


if __name__ == "__main__":
    main()
```

---

### Step 5: Blueprint Pipeline Eval Runner (`app/ai/agents/evals/blueprint_eval.py`) — Task 5.7

End-to-end blueprint execution with trace capture. Runs the full "campaign" pipeline and records per-node performance.

```python
"""Blueprint pipeline end-to-end eval runner.

Runs full blueprint pipelines with test briefs, captures per-node traces,
and measures total tokens, retries, and QA outcomes.

CLI: python -m app.ai.agents.evals.blueprint_eval \
       --output traces/blueprint_traces.jsonl \
       [--brief "Campaign brief text"]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

from app.ai.agents.evals.schemas import BlueprintEvalTrace

# Pre-built test briefs covering key pipeline scenarios
BLUEPRINT_TEST_BRIEFS: list[dict[str, str]] = [
    {
        "id": "bp-001",
        "name": "happy_path_simple",
        "brief": (
            "Create a single-column promotional email for a Spring Sale. "
            "Include a hero image placeholder, 3 product cards with prices, "
            "and a CTA button linking to the sale page. Brand: modern, clean."
        ),
    },
    {
        "id": "bp-002",
        "name": "dark_mode_recovery",
        "brief": (
            "Create a two-column newsletter for a tech company. "
            "Include a header with logo, sidebar navigation, main content area "
            "with 3 article summaries, and a footer. Must pass dark mode QA checks."
        ),
    },
    {
        "id": "bp-003",
        "name": "complex_layout_retry",
        "brief": (
            "Create a product launch email with hero section, feature comparison table "
            "(3 tiers), testimonial carousel section, pricing grid, and dual CTA buttons. "
            "Must be under 102KB for Gmail. Outlook-safe with VML buttons."
        ),
    },
    {
        "id": "bp-004",
        "name": "vague_brief",
        "brief": "Make a welcome email for new users.",
    },
    {
        "id": "bp-005",
        "name": "accessibility_heavy",
        "brief": (
            "Create a healthcare appointment reminder email. Must be fully accessible: "
            "WCAG AA contrast, semantic headings, descriptive alt text, table roles, "
            "lang attribute. Include appointment details, provider info, and cancel link."
        ),
    },
]


async def run_blueprint_eval(
    brief: str,
    brief_id: str,
    blueprint_name: str = "campaign",
) -> BlueprintEvalTrace:
    """Execute a single blueprint pipeline and capture trace."""
    from app.ai.blueprints.service import BlueprintService

    service = BlueprintService()

    start = time.monotonic()
    error: str | None = None
    run_id = ""
    total_steps = 0
    total_retries = 0
    qa_passed: bool | None = None
    final_html_length = 0
    total_tokens = 0
    node_trace: list[dict[str, object]] = []

    try:
        from app.ai.blueprints.schemas import BlueprintRunRequest

        request = BlueprintRunRequest(blueprint_name=blueprint_name, brief=brief)
        response = await service.run(request)

        run_id = response.run_id
        total_steps = len(response.progress)
        qa_passed = response.qa_passed
        final_html_length = len(response.html) if response.html else 0
        total_tokens = response.model_usage.get("total_tokens", 0)

        for p in response.progress:
            node_trace.append(
                {
                    "node_name": p.node_name,
                    "node_type": p.node_type,
                    "status": p.status,
                    "iteration": p.iteration,
                    "duration_ms": p.duration_ms,
                    "summary": p.summary,
                }
            )
            if p.iteration > 0:
                total_retries += 1

    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    elapsed = time.monotonic() - start

    return BlueprintEvalTrace(
        run_id=run_id or brief_id,
        blueprint_name=blueprint_name,
        brief=brief,
        total_steps=total_steps,
        total_retries=total_retries,
        qa_passed=qa_passed,
        final_html_length=final_html_length,
        total_tokens=total_tokens,
        elapsed_seconds=round(elapsed, 2),
        node_trace=node_trace,
        error=error,
    )


async def run_all_blueprints(
    briefs: list[dict[str, str]],
    output_path: Path,
) -> list[BlueprintEvalTrace]:
    """Run all blueprint test briefs sequentially and write JSONL traces."""
    traces: list[BlueprintEvalTrace] = []

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w") as f:
        for brief_def in briefs:
            print(f"  Running {brief_def['id']}: {brief_def['name']}...", flush=True)
            trace = await run_blueprint_eval(
                brief=brief_def["brief"],
                brief_id=brief_def["id"],
            )
            traces.append(trace)

            # Write trace as JSONL
            trace_dict: dict[str, Any] = {
                "run_id": trace.run_id,
                "blueprint_name": trace.blueprint_name,
                "brief": trace.brief,
                "total_steps": trace.total_steps,
                "total_retries": trace.total_retries,
                "qa_passed": trace.qa_passed,
                "final_html_length": trace.final_html_length,
                "total_tokens": trace.total_tokens,
                "elapsed_seconds": trace.elapsed_seconds,
                "node_trace": trace.node_trace,
                "error": trace.error,
            }
            f.write(json.dumps(trace_dict) + "\n")
            f.flush()

            status = "PASS" if trace.qa_passed else ("ERROR" if trace.error else "FAIL")
            print(f"    -> {status} ({trace.total_steps} steps, {trace.total_retries} retries, "
                  f"{trace.elapsed_seconds:.1f}s, {trace.total_tokens} tokens)")

    return traces


def print_summary(traces: list[BlueprintEvalTrace]) -> None:
    """Print summary statistics for all blueprint eval runs."""
    total = len(traces)
    errors = sum(1 for t in traces if t.error)
    qa_passed = sum(1 for t in traces if t.qa_passed)
    qa_failed = total - qa_passed - errors

    avg_steps = sum(t.total_steps for t in traces) / total if total else 0
    avg_retries = sum(t.total_retries for t in traces) / total if total else 0
    avg_tokens = sum(t.total_tokens for t in traces) / total if total else 0
    avg_time = sum(t.elapsed_seconds for t in traces) / total if total else 0

    print(f"\n=== Blueprint Pipeline Eval ===")
    print(f"Runs: {total} (qa_passed={qa_passed}, qa_failed={qa_failed}, errors={errors})")
    print(f"QA pass rate: {qa_passed / (total - errors):.1%}" if (total - errors) > 0 else "N/A")
    print(f"Avg steps: {avg_steps:.1f}, Avg retries: {avg_retries:.1f}")
    print(f"Avg tokens: {avg_tokens:.0f}, Avg time: {avg_time:.1f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run blueprint pipeline evals")
    parser.add_argument("--output", required=True, help="Path to write JSONL traces")
    parser.add_argument("--brief", help="Single brief to run (instead of all test briefs)")
    args = parser.parse_args()

    output_path = Path(args.output)

    if args.brief:
        briefs = [{"id": "custom-001", "name": "custom", "brief": args.brief}]
    else:
        briefs = BLUEPRINT_TEST_BRIEFS

    print(f"Running {len(briefs)} blueprint eval(s)...")
    traces = asyncio.run(run_all_blueprints(briefs, output_path))
    print_summary(traces)
    print(f"\nTraces: {output_path}")


if __name__ == "__main__":
    main()
```

---

### Step 6: Regression Detection (`app/ai/agents/evals/regression.py`) — Task 5.8

Compares current eval run pass rates against a stored baseline. Used in CI to gate deployments.

```python
"""Regression detection: compare current eval results against baseline.

Compares per-criterion pass rates from current eval run against stored
baseline. Flags regression if any criterion drops by more than tolerance.

CLI: python -m app.ai.agents.evals.regression \
       --current traces/analysis.json \
       --baseline traces/baseline.json \
       --tolerance 0.10 \
       [--update-baseline]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from app.ai.agents.evals.schemas import RegressionReport


def compare_pass_rates(
    current: dict[str, dict[str, float]],
    baseline: dict[str, dict[str, float]],
    tolerance: float,
) -> list[RegressionReport]:
    """Compare pass rates per agent, flag regressions beyond tolerance.

    Args:
        current: {agent: {criterion: pass_rate}} from current run
        baseline: same format from baseline
        tolerance: max acceptable drop (e.g., 0.10 = 10%)
    """
    reports: list[RegressionReport] = []

    all_agents = sorted(set(list(current.keys()) + list(baseline.keys())))

    for agent in all_agents:
        curr_rates = current.get(agent, {})
        base_rates = baseline.get(agent, {})

        if not base_rates:
            # New agent — no baseline to compare
            curr_avg = sum(curr_rates.values()) / len(curr_rates) if curr_rates else 0.0
            reports.append(
                RegressionReport(
                    agent=agent,
                    current_pass_rate=curr_avg,
                    baseline_pass_rate=0.0,
                    delta=curr_avg,
                    regressed_criteria=[],
                    improved_criteria=list(curr_rates.keys()),
                    is_regression=False,
                )
            )
            continue

        regressed: list[str] = []
        improved: list[str] = []

        all_criteria = sorted(set(list(curr_rates.keys()) + list(base_rates.keys())))
        for criterion in all_criteria:
            curr_val = curr_rates.get(criterion, 0.0)
            base_val = base_rates.get(criterion, 0.0)
            delta = curr_val - base_val

            if delta < -tolerance:
                regressed.append(criterion)
            elif delta > tolerance:
                improved.append(criterion)

        curr_avg = sum(curr_rates.values()) / len(curr_rates) if curr_rates else 0.0
        base_avg = sum(base_rates.values()) / len(base_rates) if base_rates else 0.0

        reports.append(
            RegressionReport(
                agent=agent,
                current_pass_rate=round(curr_avg, 4),
                baseline_pass_rate=round(base_avg, 4),
                delta=round(curr_avg - base_avg, 4),
                regressed_criteria=regressed,
                improved_criteria=improved,
                is_regression=len(regressed) > 0,
            )
        )

    return reports


def build_regression_report(reports: list[RegressionReport]) -> dict[str, Any]:
    """Build JSON-serializable regression report."""
    any_regression = any(r.is_regression for r in reports)

    return {
        "has_regression": any_regression,
        "agents_checked": len(reports),
        "agents_regressed": sum(1 for r in reports if r.is_regression),
        "details": [
            {
                "agent": r.agent,
                "current_pass_rate": r.current_pass_rate,
                "baseline_pass_rate": r.baseline_pass_rate,
                "delta": r.delta,
                "is_regression": r.is_regression,
                "regressed_criteria": r.regressed_criteria,
                "improved_criteria": r.improved_criteria,
            }
            for r in reports
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect eval regressions vs baseline")
    parser.add_argument("--current", required=True, help="Path to current analysis JSON")
    parser.add_argument("--baseline", required=True, help="Path to baseline analysis JSON")
    parser.add_argument("--tolerance", type=float, default=0.10, help="Max acceptable drop (default: 0.10)")
    parser.add_argument("--update-baseline", action="store_true", help="Update baseline with current results")
    args = parser.parse_args()

    current_path = Path(args.current)
    baseline_path = Path(args.baseline)

    with current_path.open() as f:
        current_data = json.load(f)
    current_rates: dict[str, dict[str, float]] = current_data.get("pass_rates", {})

    if not baseline_path.exists():
        print(f"No baseline found at {baseline_path}. Creating from current run.")
        shutil.copy2(current_path, baseline_path)
        print(f"Baseline created: {baseline_path}")
        return

    with baseline_path.open() as f:
        baseline_data = json.load(f)
    baseline_rates: dict[str, dict[str, float]] = baseline_data.get("pass_rates", {})

    reports = compare_pass_rates(current_rates, baseline_rates, args.tolerance)
    report = build_regression_report(reports)

    # Print summary
    print(f"\n=== Regression Check (tolerance={args.tolerance:.0%}) ===")
    for detail in report["details"]:
        status = "REGRESSED" if detail["is_regression"] else "OK"
        print(f"  {detail['agent']}: {detail['baseline_pass_rate']:.1%} -> "
              f"{detail['current_pass_rate']:.1%} ({detail['delta']:+.1%}) [{status}]")
        if detail["regressed_criteria"]:
            print(f"    Regressed: {', '.join(detail['regressed_criteria'])}")

    if args.update_baseline and not report["has_regression"]:
        shutil.copy2(current_path, baseline_path)
        print(f"\nBaseline updated: {baseline_path}")
    elif args.update_baseline and report["has_regression"]:
        print(f"\nBaseline NOT updated (regression detected).")

    if report["has_regression"]:
        print(f"\nREGRESSION DETECTED — {report['agents_regressed']} agent(s) regressed.")
        sys.exit(1)
    else:
        print(f"\nNo regressions detected.")


if __name__ == "__main__":
    main()
```

---

### Step 7: Makefile Targets

Add to `Makefile`:

```makefile
# ── Eval Pipeline ──
eval-run:                    ## Run agent evals (generate traces)
	python -m app.ai.agents.evals.runner --agent all --output traces/

eval-judge:                  ## Run judges on traces (generate verdicts)
	python -m app.ai.agents.evals.judge_runner --agent all --traces traces --output traces

eval-labels:                 ## Scaffold human label templates from traces+verdicts
	python -m app.ai.agents.evals.scaffold_labels --verdicts traces/scaffolder_verdicts.jsonl --traces traces/scaffolder_traces.jsonl --output traces/scaffolder_human_labels.jsonl
	python -m app.ai.agents.evals.scaffold_labels --verdicts traces/dark_mode_verdicts.jsonl --traces traces/dark_mode_traces.jsonl --output traces/dark_mode_human_labels.jsonl
	python -m app.ai.agents.evals.scaffold_labels --verdicts traces/content_verdicts.jsonl --traces traces/content_traces.jsonl --output traces/content_human_labels.jsonl

eval-analysis:               ## Analyze judge verdicts (failure taxonomy)
	python -m app.ai.agents.evals.error_analysis --verdicts traces --output traces/analysis.json

eval-blueprint:              ## Run blueprint pipeline evals
	python -m app.ai.agents.evals.blueprint_eval --output traces/blueprint_traces.jsonl

eval-regression:             ## Check for eval regressions vs baseline
	python -m app.ai.agents.evals.regression --current traces/analysis.json --baseline traces/baseline.json

eval-check: eval-analysis eval-regression  ## Full eval CI gate (analysis + regression check)
```

> **TODO:** Add `.github/workflows/eval.yml` GitHub Actions workflow to run `make eval-check` on PRs once the eval pipeline is stable and baselines are established.

---

### Step 8: Unit Tests

Create `app/ai/agents/evals/tests/__init__.py` (empty).

#### `test_error_analysis.py`

Test cluster_failures, compute_pass_rates, and build_analysis_report with synthetic verdict data. Key cases:
- All passing verdicts -> empty clusters, 100% pass rates
- Mixed pass/fail -> correct clustering by (agent, criterion)
- Verdicts with errors -> excluded from analysis
- Top failures sorted by count descending
- Pass rates computed correctly per criterion

Use inline JSONL-style dicts (no file I/O in unit tests).

#### `test_calibration.py`

Test calibrate() and CalibrationResult properties with synthetic label/verdict pairs:
- Perfect agreement -> TPR=1.0, TNR=1.0, meets_targets=True
- All false positives -> TPR=0, TNR=0
- Mixed results -> correct TP/TN/FP/FN counts
- Missing judge verdicts -> skipped gracefully
- meets_targets boundary: TPR=0.85 exactly passes, 0.84 fails

#### `test_qa_calibration.py`

Test calibrate_qa() with mock QA results and human labels:
- Perfect agreement -> 100% agreement rate
- All disagreement -> 0% agreement, correct false_pass/false_fail rates
- Labels for non-QA criteria -> ignored
- Missing traces -> skipped

#### `test_blueprint_eval.py`

Test BlueprintEvalTrace dataclass construction and print_summary with synthetic traces:
- Successful trace with all fields
- Error trace with error string
- Summary stats computation (averages)

#### `test_regression.py`

Test compare_pass_rates with synthetic baseline/current data:
- No change -> no regression
- Drop within tolerance -> no regression
- Drop beyond tolerance -> regression flagged, correct criteria listed
- New agent (no baseline) -> not flagged as regression
- Improvement -> captured in improved_criteria

---

### Step 9: Update `app/ai/agents/evals/__init__.py`

Add exports for new modules so they're importable:

```python
from app.ai.agents.evals.judges import JUDGE_REGISTRY

__all__ = ["JUDGE_REGISTRY"]
```

No need to re-export all analysis modules — they're used via CLI. Keep the init minimal.

---

## Data Flow Summary

```
[5.3] make eval-run     -> traces/{agent}_traces.jsonl        (36 agent outputs)
      make eval-judge    -> traces/{agent}_verdicts.jsonl      (36 judge verdicts)
[5.4] make eval-analysis -> traces/analysis.json               (failure taxonomy + pass rates)
[5.5] make eval-labels   -> traces/{agent}_human_labels.jsonl  (prefilled templates)
      (human fills in human_pass true/false)
      python -m ...calibration -> traces/{agent}_calibration.json (TPR/TNR per criterion)
[5.6] python -m ...qa_calibration -> traces/qa_calibration.json (QA check agreement rates)
[5.7] make eval-blueprint -> traces/blueprint_traces.jsonl     (pipeline E2E traces)
[5.8] make eval-check    -> regression check against traces/baseline.json
```

## Human Labeling Workflow (5.5)

1. Run `make eval-labels` to scaffold prefilled templates from traces + verdicts
2. Each file contains rows like:
```jsonl
{"trace_id": "scaff-001", "agent": "scaffolder", "criterion": "brief_fidelity", "judge_pass": true, "human_pass": null, "notes": ""}
{"trace_id": "scaff-001", "agent": "scaffolder", "criterion": "dark_mode", "judge_pass": null, "human_pass": null, "notes": ""}
```
3. Review agent outputs and set `human_pass` to `true` or `false` for each row
4. One file per agent — contains both judge criteria and QA check criteria
5. Target: 20 labeled traces per agent (= ~300 label rows per agent including QA criteria)

## Verification

- [ ] `make lint` passes (ruff format + check)
- [ ] `make types` passes (mypy + pyright)
- [ ] `make test` passes (all existing + new unit tests)
- [ ] CLI commands work: `python -m app.ai.agents.evals.error_analysis --help`
- [ ] CLI commands work: `python -m app.ai.agents.evals.scaffold_labels --help`
- [ ] CLI commands work: `python -m app.ai.agents.evals.calibration --help`
- [ ] CLI commands work: `python -m app.ai.agents.evals.qa_calibration --help`
- [ ] CLI commands work: `python -m app.ai.agents.evals.blueprint_eval --help`
- [ ] CLI commands work: `python -m app.ai.agents.evals.regression --help`
- [ ] Makefile targets: `make eval-analysis`, `make eval-labels`, `make eval-check`

## Implementation Order

1. `schemas.py` — shared data structures (no deps)
2. `error_analysis.py` + `tests/test_error_analysis.py` — read-only analysis (no async, no external deps)
3. `scaffold_labels.py` — label template generator (no async, reads JSONL)
4. `calibration.py` + `tests/test_calibration.py` — read-only comparison (no async)
5. `qa_calibration.py` + `tests/test_qa_calibration.py` — async (imports QA checks)
6. `blueprint_eval.py` + `tests/test_blueprint_eval.py` — async (imports BlueprintService)
7. `regression.py` + `tests/test_regression.py` — read-only comparison
8. Makefile targets
9. Update `__init__.py`
10. Verification: `make check`
