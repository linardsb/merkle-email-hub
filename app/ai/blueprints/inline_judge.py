"""Inline LLM judge adapter for live blueprint recovery retries.

Bridges the eval JUDGE_REGISTRY into the blueprint engine, converting
live NodeContext + BlueprintRun into a JudgeInput that eval judges accept.
Only invoked on recovery retries (iteration > 0) to bound cost.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.ai.agents.evals.judges import JUDGE_REGISTRY
from app.ai.agents.evals.judges.schemas import JudgeInput, JudgeVerdict
from app.ai.protocols import CompletionResponse, Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.ai.blueprints.engine import BlueprintRun
    from app.ai.blueprints.protocols import NodeContext

logger = get_logger(__name__)


def _build_judge_input(
    agent_name: str,
    context: NodeContext,
    html_output: str,
    run: BlueprintRun,
) -> JudgeInput:
    """Build a JudgeInput from live blueprint context.

    Maps live context fields to the trace-based JudgeInput schema that
    eval judges expect:
    - input_data: brief + QA failures (what the agent was asked to fix)
    - output_data: the HTML the agent produced
    - expected_challenges: derived from QA failure details
    """
    return JudgeInput(
        trace_id=f"inline-{run.run_id}-{uuid.uuid4().hex[:8]}",
        agent=agent_name,
        input_data={
            "brief": context.brief,
            "qa_failures": context.qa_failures,
            "iteration": context.iteration,
        },
        output_data={
            "html": html_output,
        },
        expected_challenges=[f.check_name for f in run.qa_failure_details],
    )


async def run_inline_judge(
    agent_name: str,
    context: NodeContext,
    html_output: str,
    run: BlueprintRun,
) -> JudgeVerdict | None:
    """Run the eval judge for an agent inline during a recovery retry.

    Returns the JudgeVerdict, or None if:
    - No judge is registered for this agent
    - The LLM call fails (failure-safe: log and return None)

    Uses the lightweight model tier and temperature=0.0 for determinism.
    """
    judge_cls = JUDGE_REGISTRY.get(agent_name)
    if judge_cls is None:
        logger.debug(
            "blueprint.inline_judge_skipped",
            agent=agent_name,
            reason="no_judge_registered",
        )
        return None

    judge = judge_cls()
    judge_input = _build_judge_input(agent_name, context, html_output, run)
    prompt = judge.build_prompt(judge_input)

    try:
        settings = get_settings()
        registry = get_registry()
        provider = registry.get_llm(settings.ai.provider)
        model = resolve_model("lightweight")

        response: CompletionResponse = await provider.complete(
            [Message(role="user", content=prompt)],
            temperature=0.0,
            model=model,
        )

        verdict = judge.parse_response(response.content, judge_input)

        logger.info(
            "blueprint.inline_judge_completed",
            agent=agent_name,
            overall_pass=verdict.overall_pass,
            criteria_count=len(verdict.criteria_results),
            run_id=run.run_id,
        )

        return verdict

    except Exception:
        logger.warning(
            "blueprint.inline_judge_failed",
            agent=agent_name,
            run_id=run.run_id,
            exc_info=True,
        )
        return None
