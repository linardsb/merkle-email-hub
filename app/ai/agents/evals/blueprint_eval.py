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
import time
from pathlib import Path
from typing import Any

from app.ai.agents.evals.schemas import BlueprintEvalTrace

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
    from app.ai.blueprints.schemas import BlueprintRunRequest
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
            print(
                f"    -> {status} ({trace.total_steps} steps, "
                f"{trace.total_retries} retries, "
                f"{trace.elapsed_seconds:.1f}s, {trace.total_tokens} tokens)"
            )

    return traces


def print_summary(traces: list[BlueprintEvalTrace]) -> None:
    """Print summary statistics for all blueprint eval runs."""
    total = len(traces)
    if total == 0:
        print("\nNo traces to summarize.")
        return

    errors = sum(1 for t in traces if t.error)
    qa_passed = sum(1 for t in traces if t.qa_passed)
    non_error = total - errors

    avg_steps = sum(t.total_steps for t in traces) / total
    avg_retries = sum(t.total_retries for t in traces) / total
    avg_tokens = sum(t.total_tokens for t in traces) / total
    avg_time = sum(t.elapsed_seconds for t in traces) / total

    print("\n=== Blueprint Pipeline Eval ===")
    print(
        f"Runs: {total} (qa_passed={qa_passed}, qa_failed={non_error - qa_passed}, errors={errors})"
    )
    if non_error > 0:
        print(f"QA pass rate: {qa_passed / non_error:.1%}")
    print(f"Avg steps: {avg_steps:.1f}, Avg retries: {avg_retries:.1f}")
    print(f"Avg tokens: {avg_tokens:.0f}, Avg time: {avg_time:.1f}s")


def main() -> None:
    """CLI entry point for blueprint pipeline evals."""
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
