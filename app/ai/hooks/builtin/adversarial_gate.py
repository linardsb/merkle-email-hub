"""Adversarial gate hook — evaluator agent post-agent gate (strict profile)."""

from __future__ import annotations

from typing import Any

from app.ai.hooks.registry import HookContext, HookEvent, HookRegistry
from app.core.exceptions import HookAbortError
from app.core.logging import get_logger

logger = get_logger(__name__)


async def _on_post_agent(ctx: HookContext) -> dict[str, Any] | None:
    """Run evaluator agent on the agent's output. Abort on reject verdict."""
    if ctx.agent_name is None:
        return None

    try:
        from app.ai.agents.evaluator.service import EvaluatorAgentService
        from app.core.config import get_settings

        settings = get_settings()
        if not settings.ai.evaluator.enabled:
            return None

        evaluator = EvaluatorAgentService()
        # Extract HTML output from artifact store if available
        html_output = ""
        if ctx.artifacts:
            from app.ai.pipeline.artifacts import HtmlArtifact

            html_artifact = ctx.artifacts.get_optional("html", HtmlArtifact)
            if html_artifact:
                html_output = html_artifact.html

        if not html_output:
            return None

        response = await evaluator.evaluate(
            original_brief="",
            agent_name=ctx.agent_name,
            agent_output=html_output,
        )

        eval_verdict = response.verdict
        if eval_verdict.verdict == "reject":
            raise HookAbortError(
                hook_name="adversarial_gate",
                reason=f"Evaluator rejected {ctx.agent_name} output: {eval_verdict.feedback[:200]}",
            )

        return {"verdict": eval_verdict.verdict, "score": eval_verdict.score}

    except HookAbortError:
        raise
    except Exception as exc:
        logger.warning(
            "hooks.adversarial_gate.degraded",
            extra={
                "agent": ctx.agent_name,
                "error": str(exc),
            },
        )
        return None


def register(registry: HookRegistry) -> None:
    """Register adversarial gate hook."""
    registry.register(
        HookEvent.POST_AGENT,
        _on_post_agent,
        name="adversarial_gate",
        profile="strict",
    )
