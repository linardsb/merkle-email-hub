"""Deterministic micro-judges: map eval judge criteria to QA checks.

For each (agent, criterion) pair, defines which QA check(s) can replace the
LLM judge. Criteria mapped to QA checks produce deterministic, reproducible
verdicts without LLM calls — saving ~60% of judge tokens per eval run.

CLI (coverage report):
    python -m app.ai.agents.evals.judge_criteria_map \
        --traces traces/ --output traces/qa_coverage.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.ai.agents.evals.judges.schemas import CriterionResult
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class CriteriaMapping:
    """Maps one judge criterion to zero or more QA checks."""

    criterion: str
    qa_checks: list[str]  # Empty = LLM-only (no deterministic replacement)
    strategy: str = "all"  # "all" = every check must pass; "any" = at least one
    notes: str = ""  # Why this mapping exists or why it's LLM-only


# ── Static Mapping ──────────────────────────────────────────────────────
# Each agent's 5 judge criteria mapped to QA check names.
# Empty qa_checks = requires LLM reasoning, no deterministic replacement.

JUDGE_CRITERIA_MAP: dict[str, list[CriteriaMapping]] = {
    "scaffolder": [
        CriteriaMapping(
            criterion="brief_fidelity",
            qa_checks=[],
            notes="Requires LLM reasoning to assess brief-to-HTML fidelity",
        ),
        CriteriaMapping(
            criterion="email_layout_patterns",
            qa_checks=["html_validation"],
            notes="Table layouts, role=presentation, 600px max — covered by html_validation DOM checks",
        ),
        CriteriaMapping(
            criterion="mso_conditional_correctness",
            qa_checks=["fallback"],
            notes="MSO conditional balance, VML nesting — covered by fallback MSO parser",
        ),
        CriteriaMapping(
            criterion="dark_mode_readiness",
            qa_checks=["dark_mode"],
            notes="Meta tags, @media queries — covered by dark_mode check",
        ),
        CriteriaMapping(
            criterion="accessibility_baseline",
            qa_checks=["accessibility"],
            notes="lang, roles, alt text, headings — covered by accessibility WCAG checks",
        ),
        CriteriaMapping(
            criterion="design_fidelity",
            qa_checks=[],
            notes="LLM-only: compares output HTML against Figma design tokens when design_context present",
        ),
    ],
    "dark_mode": [
        CriteriaMapping(
            criterion="color_coherence",
            qa_checks=[],
            notes="Requires LLM visual judgment for color pairing quality",
        ),
        CriteriaMapping(
            criterion="html_preservation",
            qa_checks=["html_validation"],
            notes="Structure preservation — html_validation catches missing elements",
        ),
        CriteriaMapping(
            criterion="outlook_selector_completeness",
            qa_checks=["dark_mode"],
            notes="[data-ogsc]/[data-ogsb] selectors — covered by dark_mode Outlook override check",
        ),
        CriteriaMapping(
            criterion="meta_and_media_query",
            qa_checks=["dark_mode"],
            notes="color-scheme meta + @media block — covered by dark_mode check",
        ),
        CriteriaMapping(
            criterion="contrast_preservation",
            qa_checks=["accessibility"],
            notes="4.5:1 WCAG AA contrast — covered by accessibility contrast checks",
        ),
    ],
    "content": [
        CriteriaMapping(
            criterion="copy_quality",
            qa_checks=[],
            notes="Requires LLM reasoning for copy quality assessment",
        ),
        CriteriaMapping(
            criterion="tone_accuracy",
            qa_checks=[],
            notes="Requires LLM reasoning for tone matching",
        ),
        CriteriaMapping(
            criterion="spam_avoidance",
            qa_checks=["spam_score"],
            notes="Spam triggers, ALL CAPS, punctuation — covered by spam_score 59-trigger database",
        ),
        CriteriaMapping(
            criterion="operation_compliance",
            qa_checks=[],
            notes="Requires LLM reasoning for operation-specific rule checking",
        ),
        CriteriaMapping(
            criterion="security_and_pii",
            qa_checks=[],
            notes="PII detection requires pattern matching beyond current QA checks; candidate for future deterministic check",
        ),
    ],
    "outlook_fixer": [
        CriteriaMapping(
            criterion="mso_conditional_correctness",
            qa_checks=["fallback"],
            notes="MSO conditional balance and structure — covered by fallback MSO parser",
        ),
        CriteriaMapping(
            criterion="vml_wellformedness",
            qa_checks=["fallback"],
            notes="VML namespace, element closure, attributes — covered by fallback VML checks",
        ),
        CriteriaMapping(
            criterion="html_preservation",
            qa_checks=["html_validation"],
            notes="Content/structure preservation — html_validation catches structural issues",
        ),
        CriteriaMapping(
            criterion="fix_completeness",
            qa_checks=["fallback"],
            notes="Ghost tables, VML fallbacks present — covered by fallback completeness checks",
        ),
        CriteriaMapping(
            criterion="outlook_version_targeting",
            qa_checks=["fallback"],
            notes="Version-scoped conditionals, DPI fix — covered by fallback MSO parser",
        ),
    ],
    "accessibility": [
        CriteriaMapping(
            criterion="wcag_aa_compliance",
            qa_checks=["accessibility"],
            notes="lang, table roles, title, charset — covered by accessibility WCAG checks",
        ),
        CriteriaMapping(
            criterion="alt_text_quality",
            qa_checks=["accessibility"],
            notes="Alt text presence and quality — covered by accessibility image group checks",
        ),
        CriteriaMapping(
            criterion="contrast_ratio_accuracy",
            qa_checks=["accessibility"],
            notes="4.5:1 normal, 3:1 large text — covered by accessibility contrast checks",
        ),
        CriteriaMapping(
            criterion="semantic_structure",
            qa_checks=["accessibility"],
            notes="Heading hierarchy, link text, table semantics — covered by accessibility checks",
        ),
        CriteriaMapping(
            criterion="screen_reader_compatibility",
            qa_checks=["accessibility", "fallback"],
            notes="Table roles + VML in MSO conditionals — requires both accessibility and fallback checks",
        ),
    ],
    "personalisation": [
        CriteriaMapping(
            criterion="syntax_correctness",
            qa_checks=["personalisation_syntax"],
            notes="ESP syntax validation — covered by personalisation_syntax delimiter/block checks",
        ),
        CriteriaMapping(
            criterion="fallback_completeness",
            qa_checks=["personalisation_syntax"],
            notes="Default values for variables — covered by personalisation_syntax fallback rules",
        ),
        CriteriaMapping(
            criterion="html_preservation",
            qa_checks=["html_validation", "personalisation_syntax"],
            notes="Structure preserved + only personalisation changes — requires both checks",
        ),
        CriteriaMapping(
            criterion="platform_accuracy",
            qa_checks=["personalisation_syntax"],
            notes="Single-platform syntax enforcement — covered by personalisation_syntax platform detection",
        ),
        CriteriaMapping(
            criterion="logic_match",
            qa_checks=[],
            notes="Requires LLM reasoning to match logic to natural language requirements",
        ),
    ],
    "code_reviewer": [
        CriteriaMapping(
            criterion="issue_genuineness",
            qa_checks=[],
            notes="Requires LLM reasoning to judge whether flagged issues are real vs false positives",
        ),
        CriteriaMapping(
            criterion="suggestion_actionability",
            qa_checks=[],
            notes="Requires LLM reasoning to judge if suggestions are specific enough",
        ),
        CriteriaMapping(
            criterion="severity_accuracy",
            qa_checks=[],
            notes="Requires LLM reasoning to judge severity classification correctness",
        ),
        CriteriaMapping(
            criterion="coverage_completeness",
            qa_checks=["html_validation", "css_support", "file_size"],
            notes="Did reviewer catch all issues? Cross-check against 3 QA checks that cover the same domains",
        ),
        CriteriaMapping(
            criterion="output_format",
            qa_checks=[],
            notes="JSON schema validation — candidate for deterministic check but not yet a QA check",
        ),
    ],
    "knowledge": [
        CriteriaMapping(
            criterion="answer_accuracy",
            qa_checks=[],
            notes="Requires LLM grounding validation against retrieved context",
        ),
        CriteriaMapping(
            criterion="citation_grounding",
            qa_checks=[],
            notes="Requires LLM reasoning to verify citations match claims",
        ),
        CriteriaMapping(
            criterion="code_example_quality",
            qa_checks=["html_validation"],
            notes="Email-safe HTML in code examples — html_validation catches bad patterns",
        ),
        CriteriaMapping(
            criterion="source_relevance",
            qa_checks=[],
            notes="Requires LLM reasoning to judge source-to-question relevance",
        ),
        CriteriaMapping(
            criterion="completeness",
            qa_checks=[],
            notes="Requires LLM reasoning to judge if all question aspects are addressed",
        ),
    ],
    "innovation": [
        CriteriaMapping(
            criterion="technique_correctness",
            qa_checks=["html_validation"],
            notes="Valid HTML/CSS for prototype — html_validation catches structural issues",
        ),
        CriteriaMapping(
            criterion="fallback_quality",
            qa_checks=["html_validation"],
            notes="Static fallback renders correctly — html_validation checks structure",
        ),
        CriteriaMapping(
            criterion="client_coverage_accuracy",
            qa_checks=[],
            notes="Requires LLM reasoning to judge stated coverage % accuracy",
        ),
        CriteriaMapping(
            criterion="feasibility_assessment",
            qa_checks=[],
            notes="Requires LLM reasoning to judge risk/recommendation quality",
        ),
        CriteriaMapping(
            criterion="innovation_value",
            qa_checks=[],
            notes="Requires LLM reasoning to judge trade-off analysis quality",
        ),
    ],
}


def get_mapped_criteria(agent: str) -> list[CriteriaMapping]:
    """Return criteria that have QA check mappings (non-empty qa_checks)."""
    return [m for m in JUDGE_CRITERIA_MAP.get(agent, []) if m.qa_checks]


def get_llm_only_criteria(agent: str) -> list[CriteriaMapping]:
    """Return criteria that require LLM judges (empty qa_checks)."""
    return [m for m in JUDGE_CRITERIA_MAP.get(agent, []) if not m.qa_checks]


def get_all_qa_check_names() -> set[str]:
    """Return set of all QA check names referenced in the mapping."""
    names: set[str] = set()
    for mappings in JUDGE_CRITERIA_MAP.values():
        for m in mappings:
            names.update(m.qa_checks)
    return names


# ── Deterministic Verdict Generation ────────────────────────────────────


async def evaluate_criterion_via_qa(
    html: str,
    mapping: CriteriaMapping,
) -> CriterionResult:
    """Run QA checks for a mapped criterion and produce a CriterionResult.

    Strategy 'all': passes only when every mapped QA check passes.
    """
    from app.qa_engine.checks import ALL_CHECKS

    check_by_name = {c.name: c for c in ALL_CHECKS}

    results: list[tuple[str, bool, str]] = []
    for check_name in mapping.qa_checks:
        check = check_by_name.get(check_name)
        if check is None:
            results.append((check_name, False, f"QA check '{check_name}' not found"))
            continue
        result = await check.run(html)
        results.append((check_name, result.passed, result.details or ""))

    passed = all(r[1] for r in results) if mapping.strategy == "all" else any(r[1] for r in results)

    failed_checks = [f"{name}: {detail}" for name, ok, detail in results if not ok]
    if passed:
        reasoning = f"[DETERMINISTIC] All QA checks passed: {', '.join(mapping.qa_checks)}"
    else:
        reasoning = f"[DETERMINISTIC] QA check(s) failed: {'; '.join(failed_checks)}"

    return CriterionResult(
        criterion=mapping.criterion,
        passed=passed,
        reasoning=reasoning,
    )


# ── Coverage Report ─────────────────────────────────────────────────────


@dataclass
class CoverageSummary:
    """Coverage statistics for one agent."""

    agent: str
    total_criteria: int
    mapped_criteria: int
    llm_only_criteria: int
    mapped_names: list[str] = field(default_factory=lambda: list[str]())
    llm_only_names: list[str] = field(default_factory=lambda: list[str]())


def compute_coverage() -> list[CoverageSummary]:
    """Compute coverage statistics for all agents."""
    summaries: list[CoverageSummary] = []
    for agent, mappings in JUDGE_CRITERIA_MAP.items():
        mapped = [m for m in mappings if m.qa_checks]
        llm_only = [m for m in mappings if not m.qa_checks]
        summaries.append(
            CoverageSummary(
                agent=agent,
                total_criteria=len(mappings),
                mapped_criteria=len(mapped),
                llm_only_criteria=len(llm_only),
                mapped_names=[m.criterion for m in mapped],
                llm_only_names=[m.criterion for m in llm_only],
            )
        )
    return summaries


async def compute_agreement(
    traces_dir: Path,
) -> dict[str, dict[str, float]]:
    """Compare QA-based verdicts against LLM judge verdicts for mapped criteria.

    Returns: {agent: {criterion: agreement_rate}}
    Requires both traces and verdicts JSONL files to exist.
    """
    agreement: dict[str, dict[str, float]] = {}

    for agent, mappings in JUDGE_CRITERIA_MAP.items():
        mapped = [m for m in mappings if m.qa_checks]
        if not mapped:
            continue

        traces_path = traces_dir / f"{agent}_traces.jsonl"
        verdicts_path = traces_dir / f"{agent}_verdicts.jsonl"

        if not traces_path.exists() or not verdicts_path.exists():
            continue

        # Load traces
        traces: list[dict[str, Any]] = []
        with traces_path.open() as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    traces.append(json.loads(stripped))

        # Load LLM verdicts keyed by (trace_id, criterion)
        llm_verdicts: dict[tuple[str, str], bool] = {}
        with verdicts_path.open() as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    v = json.loads(stripped)
                    for cr in v.get("criteria_results", []):
                        llm_verdicts[(v["trace_id"], cr["criterion"])] = cr["passed"]

        # Run QA checks on each trace's HTML
        agent_agreement: dict[str, float] = {}
        for mapping in mapped:
            agree_count = 0
            total_count = 0

            for trace in traces:
                output = trace.get("output")
                if not output:
                    continue
                html: str = output.get("html", "")
                if not html:
                    continue

                trace_id: str = trace["id"]
                llm_result = llm_verdicts.get((trace_id, mapping.criterion))
                if llm_result is None:
                    continue

                qa_result = await evaluate_criterion_via_qa(html, mapping)
                if qa_result.passed == llm_result:
                    agree_count += 1
                total_count += 1

            if total_count > 0:
                agent_agreement[mapping.criterion] = agree_count / total_count

        if agent_agreement:
            agreement[agent] = agent_agreement

    return agreement


def build_coverage_report(
    summaries: list[CoverageSummary],
    agreement: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    """Build JSON-serializable coverage report."""
    total_criteria = sum(s.total_criteria for s in summaries)
    total_mapped = sum(s.mapped_criteria for s in summaries)

    agents: list[dict[str, Any]] = []
    for s in summaries:
        agent_data: dict[str, Any] = {
            "agent": s.agent,
            "total": s.total_criteria,
            "mapped": s.mapped_criteria,
            "llm_only": s.llm_only_criteria,
            "coverage_pct": round(s.mapped_criteria / s.total_criteria * 100, 1)
            if s.total_criteria
            else 0.0,
            "mapped_criteria": s.mapped_names,
            "llm_only_criteria": s.llm_only_names,
        }

        # Add per-criterion agreement rates if available
        if agreement and s.agent in agreement:
            agent_agreement = agreement[s.agent]
            criteria_detail: list[dict[str, Any]] = []
            for m in JUDGE_CRITERIA_MAP[s.agent]:
                if m.qa_checks:
                    rate = agent_agreement.get(m.criterion)
                    criteria_detail.append(
                        {
                            "criterion": m.criterion,
                            "qa_checks": m.qa_checks,
                            "agreement_rate": round(rate, 4) if rate is not None else None,
                            "promoted": rate is not None and rate >= 0.85,
                        }
                    )
            agent_data["criteria_detail"] = criteria_detail

        agents.append(agent_data)

    return {
        "total_criteria": total_criteria,
        "total_mapped": total_mapped,
        "total_llm_only": total_criteria - total_mapped,
        "overall_coverage_pct": round(total_mapped / total_criteria * 100, 1)
        if total_criteria
        else 0.0,
        "agents": agents,
    }


def print_coverage_report(report: dict[str, Any]) -> None:
    """Log the coverage report."""
    logger.info("=== QA Coverage Report ===")
    logger.info(
        f"Criteria mapped:    {report['total_mapped']}/{report['total_criteria']} "
        f"({report['overall_coverage_pct']}%)"
    )
    logger.info(
        f"Criteria LLM-only:  {report['total_llm_only']}/{report['total_criteria']} "
        f"({100.0 - report['overall_coverage_pct']:.1f}%)"
    )

    logger.info("Per-agent breakdown:")
    for agent_data in report["agents"]:
        llm_only_str = ", ".join(agent_data["llm_only_criteria"]) or "(none)"
        logger.info(
            f"  {agent_data['agent']:20s} {agent_data['mapped']}/{agent_data['total']} "
            f"mapped ({agent_data['coverage_pct']}%) — LLM-only: {llm_only_str}"
        )

        # Log agreement details if available
        if "criteria_detail" in agent_data:
            for detail in agent_data["criteria_detail"]:
                rate = detail.get("agreement_rate")
                if rate is not None:
                    status = "PROMOTED" if detail["promoted"] else "NEEDS TUNING"
                    checks_str = " + ".join(detail["qa_checks"])
                    logger.info(
                        f"    {detail['criterion']:38s} -> {checks_str:30s} {rate:.0%} {status}"
                    )


def main() -> None:
    """CLI entry point for QA coverage analysis."""
    parser = argparse.ArgumentParser(description="QA coverage analysis for judge criteria")
    parser.add_argument(
        "--traces",
        type=Path,
        default=None,
        help="Path to traces directory (for agreement analysis)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to write coverage JSON report",
    )
    args = parser.parse_args()

    summaries = compute_coverage()

    agreement: dict[str, dict[str, float]] | None = None
    if args.traces and args.traces.exists():
        logger.info("Running agreement analysis against existing traces...")
        agreement = asyncio.run(compute_agreement(args.traces))

    report = build_coverage_report(summaries, agreement)
    print_coverage_report(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report written to: {args.output}")


if __name__ == "__main__":
    main()
