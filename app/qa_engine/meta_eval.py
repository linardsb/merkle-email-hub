"""QA check meta-evaluation: measure check precision/recall against ground-truth labels.

Runs each QA check against golden references (with expected_qa labels) and optional
adversarial emails, computes confusion matrices per check, and generates threshold
recommendations when false-positive or false-negative rates exceed configured bounds.

CLI: python -m app.qa_engine.meta_eval --output traces/qa_meta_eval_latest.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.qa_engine.checks import ALL_CHECKS, QACheckProtocol

logger = get_logger(__name__)


@dataclass(frozen=True)
class LabeledSample:
    """An HTML sample with expected QA outcomes per check."""

    name: str
    html: str
    expected_qa: dict[str, str]  # values: "pass", "fail", or "skip"


@dataclass(frozen=True)
class AdversarialEmail:
    """An adversarial email designed to challenge a specific QA check."""

    name: str
    html: str
    expected_qa: dict[str, str]  # values: "pass" or "fail"
    target_check: str


@dataclass(frozen=True)
class CheckEvalResult:
    """Confusion matrix and derived metrics for one QA check."""

    check_name: str
    tp: int
    fp: int
    tn: int
    fn: int
    precision: float
    recall: float
    f1: float
    specificity: float
    current_threshold: Any = None
    recommended_threshold: Any | None = None


@dataclass(frozen=True)
class ThresholdRecommendation:
    """Suggestion to adjust a check's threshold based on FP/FN rates."""

    check_name: str
    current: Any
    recommended: Any
    improvement_f1: float
    reasoning: str


@dataclass(frozen=True)
class MetaEvalReport:
    """Full meta-evaluation report across all QA checks."""

    checks: dict[str, CheckEvalResult]
    overall_f1: float
    timestamp: datetime
    recommendations: list[ThresholdRecommendation]
    golden_count: int
    adversarial_count: int


def _safe_div(num: float, den: float) -> float:
    return num / den if den > 0 else 0.0


def _compute_metrics(
    tp: int,
    fp: int,
    tn: int,
    fn: int,
) -> tuple[float, float, float, float]:
    """Return (precision, recall, f1, specificity)."""
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    specificity = _safe_div(tn, tn + fp)
    return precision, recall, f1, specificity


class MetaEvaluator:
    """Evaluate QA check quality against ground-truth labeled samples."""

    def __init__(
        self,
        checks: list[QACheckProtocol] | None = None,
        *,
        fp_threshold: float = 0.10,
        fn_threshold: float = 0.05,
    ) -> None:
        self._checks = {c.name: c for c in (checks or ALL_CHECKS)}
        self._fp_threshold = fp_threshold
        self._fn_threshold = fn_threshold

    async def evaluate_check(
        self,
        check_name: str,
        samples: list[LabeledSample],
    ) -> CheckEvalResult:
        """Evaluate a single check against labeled samples."""
        check = self._checks.get(check_name)
        if check is None:
            return CheckEvalResult(
                check_name=check_name,
                tp=0,
                fp=0,
                tn=0,
                fn=0,
                precision=0.0,
                recall=0.0,
                f1=0.0,
                specificity=0.0,
            )

        tp = fp = tn = fn = 0
        for sample in samples:
            expected = sample.expected_qa.get(check_name)
            if expected is None or expected == "skip":
                continue

            result = await check.run(sample.html)
            actual_pass = result.passed
            expected_pass = expected == "pass"

            if actual_pass and expected_pass:
                tp += 1
            elif actual_pass and not expected_pass:
                fp += 1
            elif not actual_pass and expected_pass:
                fn += 1
            else:
                tn += 1

        precision, recall, f1, specificity = _compute_metrics(tp, fp, tn, fn)

        return CheckEvalResult(
            check_name=check_name,
            tp=tp,
            fp=fp,
            tn=tn,
            fn=fn,
            precision=precision,
            recall=recall,
            f1=f1,
            specificity=specificity,
        )

    async def evaluate_all_checks(
        self,
        golden_samples: list[LabeledSample],
        adversarial_emails: list[AdversarialEmail] | None = None,
    ) -> MetaEvalReport:
        """Run meta-evaluation across all registered checks."""
        all_samples = list(golden_samples)
        adversarial_count = 0
        if adversarial_emails:
            adversarial_count = len(adversarial_emails)
            for ae in adversarial_emails:
                all_samples.append(
                    LabeledSample(
                        name=ae.name,
                        html=ae.html,
                        expected_qa=ae.expected_qa,
                    )
                )

        check_results: dict[str, CheckEvalResult] = {}
        for check_name in self._checks:
            result = await self.evaluate_check(check_name, all_samples)
            check_results[check_name] = result

        # Macro-average F1 across checks that had samples
        evaluated = [r for r in check_results.values() if (r.tp + r.fp + r.tn + r.fn) > 0]
        overall_f1 = sum(r.f1 for r in evaluated) / len(evaluated) if evaluated else 0.0

        recommendations = self._generate_recommendations(check_results)

        return MetaEvalReport(
            checks=check_results,
            overall_f1=overall_f1,
            timestamp=datetime.now(UTC),
            recommendations=recommendations,
            golden_count=len(golden_samples),
            adversarial_count=adversarial_count,
        )

    def _generate_recommendations(
        self,
        results: dict[str, CheckEvalResult],
    ) -> list[ThresholdRecommendation]:
        """Generate threshold recommendations for checks with high FP/FN rates."""
        recs: list[ThresholdRecommendation] = []
        for name, result in results.items():
            total = result.tp + result.fp + result.tn + result.fn
            if total == 0:
                continue

            fp_rate = _safe_div(result.fp, result.fp + result.tn)
            fn_rate = _safe_div(result.fn, result.fn + result.tp)

            reasons: list[str] = []
            if fp_rate > self._fp_threshold:
                reasons.append(f"FP rate {fp_rate:.1%} exceeds {self._fp_threshold:.0%} threshold")
            if fn_rate > self._fn_threshold:
                reasons.append(f"FN rate {fn_rate:.1%} exceeds {self._fn_threshold:.0%} threshold")

            if reasons:
                recs.append(
                    ThresholdRecommendation(
                        check_name=name,
                        current=result.current_threshold,
                        recommended=None,
                        improvement_f1=0.0,
                        reasoning="; ".join(reasons),
                    )
                )
        return recs


def load_golden_samples() -> list[LabeledSample]:
    """Load golden references that have expected_qa labels.

    Reads index.yaml directly (same file as golden_references.py) to access
    the expected_qa field that only meta-eval uses.
    """
    import yaml

    from app.ai.agents.evals.golden_references import (
        _GOLDEN_REF_DIR,  # pyright: ignore[reportPrivateUsage]
    )

    index_file = _GOLDEN_REF_DIR / "index.yaml"
    raw = yaml.safe_load(index_file.read_text())

    samples: list[LabeledSample] = []
    for entry in raw["references"]:
        expected_qa_raw: dict[str, str] | None = entry.get("expected_qa")
        if not expected_qa_raw:
            continue

        # Extract snippet using same logic as golden_references
        file_name: str = entry["file"]
        path = _GOLDEN_REF_DIR / file_name
        all_lines = path.read_text().splitlines()
        if "selector" in entry and "lines" in entry["selector"]:
            start, end = entry["selector"]["lines"]
            all_lines = all_lines[max(0, start - 1) : end]
        html = "\n".join(all_lines[:80])

        samples.append(
            LabeledSample(
                name=entry["name"],
                html=html,
                expected_qa=expected_qa_raw,
            )
        )

    logger.info("meta_eval.golden_samples_loaded", count=len(samples))
    return samples


def report_to_dict(report: MetaEvalReport) -> dict[str, Any]:
    """Serialize a MetaEvalReport to a JSON-compatible dict."""
    return {
        "checks": {
            name: {
                "check_name": r.check_name,
                "tp": r.tp,
                "fp": r.fp,
                "tn": r.tn,
                "fn": r.fn,
                "precision": round(r.precision, 4),
                "recall": round(r.recall, 4),
                "f1": round(r.f1, 4),
                "specificity": round(r.specificity, 4),
                "current_threshold": r.current_threshold,
                "recommended_threshold": r.recommended_threshold,
            }
            for name, r in report.checks.items()
        },
        "overall_f1": round(report.overall_f1, 4),
        "timestamp": report.timestamp.isoformat(),
        "recommendations": [
            {
                "check_name": rec.check_name,
                "current": rec.current,
                "recommended": rec.recommended,
                "improvement_f1": round(rec.improvement_f1, 4),
                "reasoning": rec.reasoning,
            }
            for rec in report.recommendations
        ],
        "golden_count": report.golden_count,
        "adversarial_count": report.adversarial_count,
    }


_REPORT_PATH = Path("traces/qa_meta_eval_latest.json")


def save_report(report: MetaEvalReport) -> Path:
    """Write report to traces/ directory."""
    _REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = report_to_dict(report)
    _REPORT_PATH.write_text(json.dumps(data, indent=2))
    logger.info("meta_eval.report_saved", path=str(_REPORT_PATH))
    return _REPORT_PATH


def load_latest_report() -> dict[str, Any] | None:
    """Load the most recent meta-eval report from disk."""
    if not _REPORT_PATH.exists():
        return None
    return json.loads(_REPORT_PATH.read_text())  # type: ignore[no-any-return]


def main() -> None:
    """CLI entry point for QA meta-evaluation."""
    import asyncio

    parser = argparse.ArgumentParser(description="Run QA check meta-evaluation")
    parser.add_argument(
        "--output",
        default="traces/qa_meta_eval_latest.json",
        help="Path to write meta-eval report JSON",
    )
    parser.parse_args()

    samples = load_golden_samples()
    if not samples:
        logger.error("meta_eval.no_samples", msg="No golden samples with expected_qa labels found")
        sys.exit(1)

    evaluator = MetaEvaluator()
    report = asyncio.run(evaluator.evaluate_all_checks(samples))
    save_report(report)

    logger.info("=== QA Meta-Evaluation ===")
    logger.info(f"Checks evaluated: {len(report.checks)}")
    logger.info(f"Overall F1: {report.overall_f1:.2%}")
    if report.recommendations:
        logger.info(f"Recommendations ({len(report.recommendations)}):")
        for rec in report.recommendations:
            logger.info(f"  {rec.check_name}: {rec.reasoning}")


if __name__ == "__main__":
    main()
