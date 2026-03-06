# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
"""
Eval runner — executes synthetic test cases against agents and collects traces.

Usage:
    python -m app.ai.agents.evals.runner --agent scaffolder --output traces/
    python -m app.ai.agents.evals.runner --agent dark_mode --output traces/
    python -m app.ai.agents.evals.runner --agent content --output traces/
    python -m app.ai.agents.evals.runner --agent all --output traces/

Each trace includes: input, agent output, metadata, and timing.
Traces are saved as JSONL for downstream error analysis and judge evaluation.
"""

import argparse
import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.ai.agents.evals.synthetic_data_content import CONTENT_TEST_CASES
from app.ai.agents.evals.synthetic_data_dark_mode import DARK_MODE_TEST_CASES
from app.ai.agents.evals.synthetic_data_scaffolder import SCAFFOLDER_TEST_CASES


async def run_scaffolder_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run a single scaffolder test case and return the trace."""
    from app.ai.agents.scaffolder.schemas import ScaffolderRequest
    from app.ai.agents.scaffolder.service import ScaffolderService

    service = ScaffolderService()
    request = ScaffolderRequest(brief=case["brief"], stream=False, run_qa=True)

    start = time.monotonic()
    try:
        response = await service.generate(request)
        elapsed = time.monotonic() - start
        return {
            "id": case["id"],
            "agent": "scaffolder",
            "dimensions": case["dimensions"],
            "input": {"brief": case["brief"]},
            "output": {
                "html": response.html,
                "qa_results": [r.model_dump() for r in (response.qa_results or [])],
                "qa_passed": response.qa_passed,
                "model": response.model,
            },
            "expected_challenges": case["expected_challenges"],
            "elapsed_seconds": round(elapsed, 2),
            "error": None,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        elapsed = time.monotonic() - start
        return {
            "id": case["id"],
            "agent": "scaffolder",
            "dimensions": case["dimensions"],
            "input": {"brief": case["brief"]},
            "output": None,
            "expected_challenges": case["expected_challenges"],
            "elapsed_seconds": round(elapsed, 2),
            "error": f"{type(e).__name__}: {e}",
            "timestamp": datetime.now(UTC).isoformat(),
        }


async def run_dark_mode_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run a single dark mode test case and return the trace."""
    from app.ai.agents.dark_mode.schemas import DarkModeRequest
    from app.ai.agents.dark_mode.service import DarkModeService

    service = DarkModeService()
    request = DarkModeRequest(
        html=case["html_input"],
        color_overrides=case.get("color_overrides"),
        preserve_colors=case.get("preserve_colors"),
        stream=False,
        run_qa=True,
    )

    start = time.monotonic()
    try:
        response = await service.process(request)
        elapsed = time.monotonic() - start
        return {
            "id": case["id"],
            "agent": "dark_mode",
            "dimensions": case["dimensions"],
            "input": {
                "html_length": len(case["html_input"]),
                "color_overrides": case.get("color_overrides"),
                "preserve_colors": case.get("preserve_colors"),
            },
            "output": {
                "html": response.html,
                "qa_results": [r.model_dump() for r in (response.qa_results or [])],
                "qa_passed": response.qa_passed,
                "model": response.model,
            },
            "expected_challenges": case["expected_challenges"],
            "elapsed_seconds": round(elapsed, 2),
            "error": None,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        elapsed = time.monotonic() - start
        return {
            "id": case["id"],
            "agent": "dark_mode",
            "dimensions": case["dimensions"],
            "input": {
                "html_length": len(case["html_input"]),
                "color_overrides": case.get("color_overrides"),
                "preserve_colors": case.get("preserve_colors"),
            },
            "output": None,
            "expected_challenges": case["expected_challenges"],
            "elapsed_seconds": round(elapsed, 2),
            "error": f"{type(e).__name__}: {e}",
            "timestamp": datetime.now(UTC).isoformat(),
        }


async def run_content_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run a single content test case and return the trace."""
    from app.ai.agents.content.schemas import ContentRequest
    from app.ai.agents.content.service import ContentService

    service = ContentService()
    inp = case["input"]
    request = ContentRequest(
        operation=inp["operation"],
        text=inp["text"],
        tone=inp.get("tone"),
        brand_voice=inp.get("brand_voice"),
        num_alternatives=inp.get("num_alternatives", 1),
        stream=False,
    )

    start = time.monotonic()
    try:
        response = await service.generate(request)
        elapsed = time.monotonic() - start
        return {
            "id": case["id"],
            "agent": "content",
            "dimensions": case["dimensions"],
            "input": inp,
            "output": {
                "content": response.content,
                "operation": response.operation,
                "spam_warnings": [w.model_dump() for w in response.spam_warnings],
                "model": response.model,
            },
            "expected_challenges": case["expected_challenges"],
            "elapsed_seconds": round(elapsed, 2),
            "error": None,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        elapsed = time.monotonic() - start
        return {
            "id": case["id"],
            "agent": "content",
            "dimensions": case["dimensions"],
            "input": inp,
            "output": None,
            "expected_challenges": case["expected_challenges"],
            "elapsed_seconds": round(elapsed, 2),
            "error": f"{type(e).__name__}: {e}",
            "timestamp": datetime.now(UTC).isoformat(),
        }


async def run_agent(
    agent: str,
    output_dir: Path,
    *,
    dry_run: bool = False,
    batch_size: int = 5,
    delay: float = 3.0,
) -> None:
    """Run all test cases for an agent and write traces to JSONL."""
    output_dir.mkdir(parents=True, exist_ok=True)

    cases: list[dict[str, Any]]
    runner: Any
    if agent == "scaffolder":
        cases = SCAFFOLDER_TEST_CASES
        runner = run_scaffolder_case
    elif agent == "dark_mode":
        cases = DARK_MODE_TEST_CASES
        runner = run_dark_mode_case
    elif agent == "content":
        cases = CONTENT_TEST_CASES
        runner = run_content_case
    else:
        raise ValueError(f"Unknown agent: {agent}")

    output_file = output_dir / f"{agent}_traces.jsonl"
    mode_label = " (dry-run)" if dry_run else ""
    print(f"Running {len(cases)} test cases for {agent}{mode_label}...")

    traces = []
    if dry_run:
        from app.ai.agents.evals.mock_traces import generate_mock_trace

        for i, case in enumerate(cases, 1):
            print(f"  [{i}/{len(cases)}] {case['id']}... (dry-run)")
            trace = generate_mock_trace(case, agent)
            traces.append(trace)
    else:
        for i, case in enumerate(cases, 1):
            print(f"  [{i}/{len(cases)}] {case['id']}...", end=" ", flush=True)
            trace = await runner(case)
            traces.append(trace)
            status = "OK" if trace["error"] is None else f"ERROR: {trace['error']}"
            print(f"{status} ({trace['elapsed_seconds']}s)")
            if (i % batch_size == 0) and i < len(cases):
                print(f"  Rate limit pause ({delay}s)...", flush=True)
                await asyncio.sleep(delay)

    with Path.open(output_file, "w") as f:
        for trace in traces:
            f.write(json.dumps(trace) + "\n")

    passed = sum(1 for t in traces if t["error"] is None)
    print(f"\nDone: {passed}/{len(traces)} succeeded. Traces: {output_file}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run agent evals")
    parser.add_argument(
        "--agent",
        choices=["scaffolder", "dark_mode", "content", "all"],
        required=True,
    )
    parser.add_argument("--output", type=Path, default=Path("traces"))
    parser.add_argument("--dry-run", action="store_true", help="Generate mock traces without LLM")
    parser.add_argument(
        "--batch-size", type=int, default=5, help="Traces per batch before delay (default: 5)"
    )
    parser.add_argument(
        "--delay", type=float, default=3.0, help="Seconds between batches (default: 3.0)"
    )
    args = parser.parse_args()

    agents = ["scaffolder", "dark_mode", "content"] if args.agent == "all" else [args.agent]

    for agent in agents:
        await run_agent(
            agent,
            args.output,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            delay=args.delay,
        )


if __name__ == "__main__":
    asyncio.run(main())
