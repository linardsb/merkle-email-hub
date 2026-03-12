# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
"""CLI for running LLM judges on collected traces.

Usage:
    python -m app.ai.agents.evals.judge_runner \
        --agent scaffolder \
        --traces traces/scaffolder_traces.jsonl \
        --output traces/scaffolder_verdicts.jsonl
"""

import argparse
import asyncio
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.ai.agents.evals.judges import JUDGE_REGISTRY
from app.ai.agents.evals.judges.accessibility import AccessibilityJudge
from app.ai.agents.evals.judges.code_reviewer import CodeReviewerJudge
from app.ai.agents.evals.judges.content import ContentJudge
from app.ai.agents.evals.judges.dark_mode import DarkModeJudge
from app.ai.agents.evals.judges.outlook_fixer import OutlookFixerJudge
from app.ai.agents.evals.judges.personalisation import PersonalisationJudge
from app.ai.agents.evals.judges.innovation import InnovationJudge
from app.ai.agents.evals.judges.knowledge import KnowledgeJudge
from app.ai.agents.evals.judges.scaffolder import ScaffolderJudge
from app.ai.agents.evals.judges.schemas import CriterionResult, JudgeInput, JudgeVerdict
from app.ai.protocols import CompletionResponse, LLMProvider, Message
from app.ai.registry import get_registry
from app.core.config import get_settings


def load_traces(traces_path: Path) -> list[dict[str, Any]]:
    """Load JSONL traces from file, skipping errored traces (output=null)."""
    traces: list[dict[str, Any]] = []
    with Path.open(traces_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            trace = json.loads(line)
            if trace.get("output") is not None:
                traces.append(trace)
    return traces


def trace_to_judge_input(trace: dict[str, Any]) -> JudgeInput:
    """Convert a raw trace dict to a JudgeInput."""
    return JudgeInput(
        trace_id=trace["id"],
        agent=trace["agent"],
        input_data=trace["input"],
        output_data=trace["output"],
        expected_challenges=trace.get("expected_challenges", []),
    )


async def judge_trace(
    judge: ScaffolderJudge
    | DarkModeJudge
    | ContentJudge
    | OutlookFixerJudge
    | AccessibilityJudge
    | PersonalisationJudge
    | CodeReviewerJudge
    | KnowledgeJudge
    | InnovationJudge,
    trace: dict[str, Any],
    provider: LLMProvider,
    model: str,
) -> JudgeVerdict:
    """Run a single judge on a single trace."""
    judge_input = trace_to_judge_input(trace)
    prompt = judge.build_prompt(judge_input)

    try:
        response: CompletionResponse = await provider.complete(
            [Message(role="user", content=prompt)],
            temperature=0.0,
            model=model,
        )
        return judge.parse_response(response.content, judge_input)
    except Exception as e:
        return JudgeVerdict(
            trace_id=judge_input.trace_id,
            agent=judge.agent_name,
            overall_pass=False,
            criteria_results=[],
            error=f"LLM call failed: {type(e).__name__}: {e}",
        )


def print_summary(agent: str, verdicts: list[JudgeVerdict], output_path: Path) -> None:
    """Print judge results summary to stdout."""
    total = len(verdicts)
    passed = sum(1 for v in verdicts if v.overall_pass)
    errored = sum(1 for v in verdicts if v.error is not None)
    failed = total - passed - errored

    print(f"\n=== Judge Results: {agent} ===")
    print(f"Traces evaluated: {total}")
    print(f"  Passed: {passed} ({passed / total * 100:.1f}%)" if total else "  Passed: 0")
    print(f"  Failed: {failed} ({failed / total * 100:.1f}%)" if total else "  Failed: 0")
    print(f"  Errors: {errored} ({errored / total * 100:.1f}%)" if total else "  Errors: 0")

    # Per-criterion pass rates
    criterion_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"passed": 0, "total": 0})
    for v in verdicts:
        for cr in v.criteria_results:
            criterion_counts[cr.criterion]["total"] += 1
            if cr.passed:
                criterion_counts[cr.criterion]["passed"] += 1

    if criterion_counts:
        print("\nPer-criterion pass rates:")
        for name, counts in criterion_counts.items():
            rate = counts["passed"] / counts["total"] * 100 if counts["total"] else 0
            print(f"  {name:40s} {counts['passed']}/{counts['total']} ({rate:.1f}%)")

    print(f"\nVerdicts written to: {output_path}")


async def run_judge(
    agent: str,
    traces_path: Path,
    output_path: Path,
    provider_name: str | None,
    model_override: str | None,
    batch_size: int,
    delay: float,
    *,
    dry_run: bool = False,
    skip_existing: bool = False,
) -> None:
    """Run judge on all traces for an agent."""
    judge_cls = JUDGE_REGISTRY.get(agent)
    if judge_cls is None:
        raise ValueError(f"Unknown agent: {agent}. Available: {list(JUDGE_REGISTRY.keys())}")

    traces = load_traces(traces_path)

    if not traces:
        print(f"No valid traces found in {traces_path}")
        return

    # Load existing verdicts for resume capability
    verdicts: list[JudgeVerdict] = []
    existing_ids: set[str] = set()
    if skip_existing and output_path.exists():
        with Path.open(output_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    existing_ids.add(data["trace_id"])
                    verdicts.append(JudgeVerdict(**data))
        if existing_ids:
            print(f"Resuming: {len(existing_ids)} existing verdicts found in {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_mode = "a" if existing_ids else "w"

    with Path.open(output_path, file_mode) as f:
        if dry_run:
            from app.ai.agents.evals.mock_traces import AGENT_CRITERIA, generate_mock_verdict

            criteria = AGENT_CRITERIA.get(agent, [])
            print(f"Judging {len(traces)} traces for {agent} (dry-run)...")
            for i, trace in enumerate(traces, 1):
                trace_id = trace["id"]
                if trace_id in existing_ids:
                    print(f"  [{i}/{len(traces)}] {trace_id}... SKIPPED (exists)")
                    continue
                print(f"  [{i}/{len(traces)}] {trace_id}... (dry-run)")
                verdict_dict = generate_mock_verdict(trace, criteria)
                verdict = JudgeVerdict(
                    trace_id=verdict_dict["trace_id"],
                    agent=verdict_dict["agent"],
                    overall_pass=verdict_dict["overall_pass"],
                    criteria_results=[
                        CriterionResult(**cr) for cr in verdict_dict["criteria_results"]
                    ],
                    error=verdict_dict["error"],
                )
                verdicts.append(verdict)
                f.write(json.dumps(verdict.model_dump()) + "\n")
                f.flush()
        else:
            judge = judge_cls()

            # Resolve provider
            settings = get_settings()
            resolved_provider = provider_name or settings.ai.provider
            registry = get_registry()
            provider = registry.get_llm(resolved_provider)
            model = model_override or settings.ai.model

            pending_traces = [t for t in traces if t["id"] not in existing_ids]
            print(
                f"Judging {len(pending_traces)} traces for {agent} "
                f"(provider={resolved_provider}, model={model})..."
            )

            for batch_start in range(0, len(pending_traces), batch_size):
                batch = pending_traces[batch_start : batch_start + batch_size]
                batch_num = batch_start // batch_size + 1

                for trace in batch:
                    trace_id = trace["id"]
                    print(
                        f"  [{len(verdicts) + 1}/{len(traces)}] {trace_id}...",
                        end=" ",
                        flush=True,
                    )

                    start = time.monotonic()
                    verdict = await judge_trace(judge, trace, provider, model)
                    elapsed = time.monotonic() - start

                    verdicts.append(verdict)
                    f.write(json.dumps(verdict.model_dump()) + "\n")
                    f.flush()
                    status = (
                        "PASS" if verdict.overall_pass else ("ERROR" if verdict.error else "FAIL")
                    )
                    print(f"{status} ({elapsed:.1f}s)")

                # Delay between batches (not after last batch)
                if batch_start + batch_size < len(pending_traces):
                    print(f"  [batch {batch_num} complete, waiting {delay}s...]")
                    await asyncio.sleep(delay)

    print_summary(agent, verdicts, output_path)


async def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run LLM judges on agent eval traces")
    parser.add_argument(
        "--agent",
        choices=[
            "scaffolder",
            "dark_mode",
            "content",
            "outlook_fixer",
            "accessibility",
            "personalisation",
            "code_reviewer",
            "all",
        ],
        required=True,
        help="Agent to judge (or 'all')",
    )
    parser.add_argument(
        "--traces", type=Path, required=True, help="Path to JSONL traces file or directory"
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="Path to output JSONL verdicts file or directory"
    )
    parser.add_argument("--provider", type=str, default=None, help="Override AI provider")
    parser.add_argument("--model", type=str, default=None, help="Override model")
    parser.add_argument("--batch-size", type=int, default=5, help="Traces per batch (default: 5)")
    parser.add_argument(
        "--delay", type=float, default=2.0, help="Seconds between batches (default: 2.0)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Generate mock verdicts without LLM")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip traces already judged in output file (resume after crash)",
    )
    args = parser.parse_args()

    agents = (
        [
            "scaffolder",
            "dark_mode",
            "content",
            "outlook_fixer",
            "accessibility",
            "personalisation",
            "code_reviewer",
        ]
        if args.agent == "all"
        else [args.agent]
    )

    for agent in agents:
        # Resolve paths for multi-agent mode
        if args.agent == "all":
            traces_path = args.traces / f"{agent}_traces.jsonl"
            output_path = args.output / f"{agent}_verdicts.jsonl"
        else:
            traces_path = args.traces
            output_path = args.output

        if not traces_path.exists():
            print(f"Traces file not found: {traces_path}, skipping {agent}")
            continue

        await run_judge(
            agent=agent,
            traces_path=traces_path,
            output_path=output_path,
            provider_name=args.provider,
            model_override=args.model,
            batch_size=args.batch_size,
            delay=args.delay,
            dry_run=args.dry_run,
            skip_existing=args.skip_existing,
        )


if __name__ == "__main__":
    asyncio.run(main())
