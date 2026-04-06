"""Generate knowledge base document from judge calibration data.

Reads all traces/*_calibration.json files and produces a structured Markdown
document with per-agent calibration summaries, cross-agent failure patterns,
early-warning criteria, and disagreement examples.  The output is designed for
ingestion into the Knowledge agent's RAG corpus.

CLI:
    uv run python scripts/generate-calibration-knowledge.py \
        --traces-dir traces/ \
        --output data/knowledge/judge_calibration_insights.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Early-warning thresholds (above target but approaching it)
WARN_TPR_THRESHOLD = 0.90
WARN_TNR_THRESHOLD = 0.85

MAX_EXAMPLES_PER_KEY = 3


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_all_calibrations(traces_dir: Path) -> list[dict[str, Any]]:
    """Load all *_calibration.json files from the traces directory."""
    calibrations: list[dict[str, Any]] = []
    for path in sorted(traces_dir.glob("*_calibration.json")):
        try:
            data = json.loads(path.read_text())
            calibrations.append(data)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "calibration_knowledge.skip_malformed",
                path=str(path),
                error=str(exc),
            )
    return calibrations


def load_verdicts_with_reasoning(
    traces_dir: Path,
) -> dict[tuple[str, str, str], tuple[bool, str]]:
    """Load all verdict JSONL files, keyed by (agent, trace_id, criterion).

    Returns:
        Mapping of (agent, trace_id, criterion) -> (judge_passed, reasoning).
    """
    lookup: dict[tuple[str, str, str], tuple[bool, str]] = {}
    for path in sorted(traces_dir.glob("*_verdicts.jsonl")):
        try:
            with path.open() as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    verdict = json.loads(stripped)
                    if verdict.get("error"):
                        continue
                    agent: str = verdict["agent"]
                    trace_id: str = verdict["trace_id"]
                    for cr in verdict.get("criteria_results", []):
                        lookup[(agent, trace_id, cr["criterion"])] = (
                            cr["passed"],
                            cr.get("reasoning", ""),
                        )
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "calibration_knowledge.skip_malformed_verdicts",
                path=str(path),
                error=str(exc),
            )
    return lookup


def load_human_labels(
    traces_dir: Path,
) -> dict[tuple[str, str, str], bool]:
    """Load all human label JSONL files, keyed by (agent, trace_id, criterion).

    Returns:
        Mapping of (agent, trace_id, criterion) -> human_pass.
    """
    lookup: dict[tuple[str, str, str], bool] = {}
    for path in sorted(traces_dir.glob("*_human_labels.jsonl")):
        try:
            with path.open() as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    data = json.loads(stripped)
                    if data.get("human_pass") is None:
                        continue
                    lookup[(data["agent"], data["trace_id"], data["criterion"])] = data[
                        "human_pass"
                    ]
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "calibration_knowledge.skip_malformed_labels",
                path=str(path),
                error=str(exc),
            )
    return lookup


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


def _collect_all_details(calibrations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten details from all calibration reports into a single list."""
    details: list[dict[str, Any]] = []
    for cal in calibrations:
        details.extend(cal.get("details", []))
    return details


def extract_cross_agent_patterns(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find criteria that fail (meets_targets=False) across >=2 agents."""
    by_criterion: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in details:
        if not d.get("meets_targets"):
            by_criterion[d["criterion"]].append(d)

    patterns: list[dict[str, Any]] = []
    for criterion in sorted(by_criterion):
        entries = by_criterion[criterion]
        if len(entries) < 2:
            continue
        agents = sorted({e["agent"] for e in entries})
        avg_tpr = round(sum(e["tpr"] for e in entries) / len(entries), 4)
        avg_tnr = round(sum(e["tnr"] for e in entries) / len(entries), 4)
        patterns.append(
            {
                "criterion": criterion,
                "agents": agents,
                "avg_tpr": avg_tpr,
                "avg_tnr": avg_tnr,
            }
        )
    return patterns


def extract_early_warnings(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find criteria approaching failure threshold but still meeting targets.

    Early warning: meets_targets=True but TPR < 0.90 or TNR < 0.85.
    """
    warnings: list[dict[str, Any]] = []
    for d in details:
        if not d.get("meets_targets"):
            continue
        tpr = d["tpr"]
        tnr = d["tnr"]
        risks: list[str] = []
        if tpr < WARN_TPR_THRESHOLD:
            risks.append(f"TPR {tpr:.4f} < {WARN_TPR_THRESHOLD}")
        if tnr < WARN_TNR_THRESHOLD:
            risks.append(f"TNR {tnr:.4f} < {WARN_TNR_THRESHOLD}")
        if risks:
            warnings.append(
                {
                    "agent": d["agent"],
                    "criterion": d["criterion"],
                    "tpr": tpr,
                    "tnr": tnr,
                    "risk": "; ".join(risks),
                }
            )
    return sorted(warnings, key=lambda w: (w["agent"], w["criterion"]))


def extract_disagreement_examples(
    verdicts: dict[tuple[str, str, str], tuple[bool, str]],
    labels: dict[tuple[str, str, str], bool],
) -> dict[tuple[str, str], list[dict[str, str]]]:
    """Find trace IDs where judge and human disagree, grouped by (agent, criterion).

    Returns at most MAX_EXAMPLES_PER_KEY examples per (agent, criterion) key.
    Each example contains trace_id and error_type (false_positive / false_negative).
    """
    by_key: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)

    for (agent, trace_id, criterion), human_pass in sorted(labels.items()):
        verdict = verdicts.get((agent, trace_id, criterion))
        if verdict is None:
            continue
        judge_passed, _reasoning = verdict

        is_fp = judge_passed and not human_pass
        is_fn = not judge_passed and human_pass

        if is_fp or is_fn:
            error_type = "false_positive" if is_fp else "false_negative"
            by_key[(agent, criterion)].append({"trace_id": trace_id, "error_type": error_type})

    # Cap examples per key
    return {k: v[:MAX_EXAMPLES_PER_KEY] for k, v in by_key.items()}


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------


def generate_markdown(
    calibrations: list[dict[str, Any]],
    cross_patterns: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    examples: dict[tuple[str, str], list[dict[str, str]]],
) -> str:
    """Produce structured Markdown from analysis results."""
    lines: list[str] = []
    now = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")

    lines.append("# Judge Calibration Insights")
    lines.append("")
    lines.append(f"> Auto-generated on {now}. Query via Knowledge agent.")
    lines.append("")

    all_details = _collect_all_details(calibrations)

    # --- Per-agent calibration summary ---
    lines.append("## Per-Agent Calibration Summary")
    lines.append("")

    by_agent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in all_details:
        by_agent[d["agent"]].append(d)

    for agent in sorted(by_agent):
        agent_details = by_agent[agent]
        lines.append(f"### {agent}")
        lines.append("")
        lines.append("| Criterion | TPR | TNR | Status | Labels |")
        lines.append("|-----------|-----|-----|--------|--------|")

        for d in sorted(agent_details, key=lambda x: x["criterion"]):
            status = _status_label(d)
            lines.append(
                f"| {d['criterion']} | {d['tpr']:.4f} | {d['tnr']:.4f} "
                f"| {status} | {d['total_labels']} |"
            )
        lines.append("")

    # --- Early warnings ---
    lines.append("## Criteria Approaching Failure Threshold")
    lines.append("")

    if warnings:
        lines.append("| Agent | Criterion | TPR | TNR | Risk |")
        lines.append("|-------|-----------|-----|-----|------|")
        for w in warnings:
            lines.append(
                f"| {w['agent']} | {w['criterion']} | {w['tpr']:.4f} "
                f"| {w['tnr']:.4f} | {w['risk']} |"
            )
    else:
        lines.append("No criteria currently approaching failure threshold.")
    lines.append("")

    # --- Cross-agent patterns ---
    lines.append("## Cross-Agent Patterns")
    lines.append("")

    if cross_patterns:
        for cp in cross_patterns:
            agent_list = ", ".join(cp["agents"])
            lines.append(f"### {cp['criterion']} — fails in {len(cp['agents'])} agents")
            lines.append("")
            lines.append(
                f"Agents: {agent_list}. Average TPR: {cp['avg_tpr']:.4f}, TNR: {cp['avg_tnr']:.4f}."
            )
            lines.append("")
    else:
        lines.append("No criteria currently failing across multiple agents.")
    lines.append("")

    # --- Disagreement patterns ---
    lines.append("## Common Disagreement Patterns")
    lines.append("")

    if examples:
        for agent, criterion in sorted(examples):
            items = examples[(agent, criterion)]
            fp_count = sum(1 for e in items if e["error_type"] == "false_positive")
            fn_count = sum(1 for e in items if e["error_type"] == "false_negative")

            if fp_count > fn_count:
                bias = "FP-heavy"
            elif fn_count > fp_count:
                bias = "FN-heavy"
            else:
                bias = "mixed"

            trace_ids = ", ".join(e["trace_id"] for e in items)
            lines.append(f"### {agent}: {criterion}")
            lines.append("")
            lines.append(f"- Type: {bias}")
            lines.append(f"- Example traces: {trace_ids}")
            lines.append("")
    else:
        lines.append("No disagreements found between judges and human labels.")
    lines.append("")

    return "\n".join(lines)


def _status_label(detail: dict[str, Any]) -> str:
    """Return a status label: PASS, WARN, or FAIL."""
    if not detail.get("meets_targets"):
        return "FAIL"
    tpr = detail["tpr"]
    tnr = detail["tnr"]
    if tpr < WARN_TPR_THRESHOLD or tnr < WARN_TNR_THRESHOLD:
        return "WARN"
    return "PASS"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for calibration knowledge generation."""
    parser = argparse.ArgumentParser(
        description="Generate knowledge base document from judge calibration data"
    )
    parser.add_argument(
        "--traces-dir",
        default="traces/",
        help="Directory containing calibration JSON and verdict/label JSONL files",
    )
    parser.add_argument(
        "--output",
        default="data/knowledge/judge_calibration_insights.md",
        help="Path to write the generated Markdown document",
    )
    args = parser.parse_args()

    traces_dir = Path(args.traces_dir)
    output_path = Path(args.output)

    # Load calibration data
    calibrations = load_all_calibrations(traces_dir)
    if not calibrations:
        logger.error(
            "calibration_knowledge.no_calibration_files",
            traces_dir=str(traces_dir),
        )
        sys.exit(1)

    all_details = _collect_all_details(calibrations)

    # Load verdicts and labels for disagreement extraction
    verdicts = load_verdicts_with_reasoning(traces_dir)
    labels = load_human_labels(traces_dir)

    # Analyse
    cross_patterns = extract_cross_agent_patterns(all_details)
    warnings = extract_early_warnings(all_details)
    examples = extract_disagreement_examples(verdicts, labels)

    # Generate markdown
    markdown = generate_markdown(calibrations, cross_patterns, warnings, examples)

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown)

    logger.info(
        "calibration_knowledge.generate_completed",
        output=str(output_path),
        agents=len({d["agent"] for d in all_details}),
        criteria=len(all_details),
        cross_patterns=len(cross_patterns),
        early_warnings=len(warnings),
        disagreement_keys=len(examples),
    )


if __name__ == "__main__":
    main()
