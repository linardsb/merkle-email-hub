# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Evaluator agentic node — adversarial evaluation of upstream agent output."""

from __future__ import annotations

from app.ai.agents.evaluator import get_evaluator_service
from app.ai.agents.evaluator.prompt import _load_criteria
from app.ai.blueprints.protocols import (
    AgentHandoff,
    HandoffStatus,
    NodeContext,
    NodeResult,
    NodeType,
)
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _load_criteria_names(agent_name: str) -> list[str]:
    """Load criteria names for an agent from YAML."""
    criteria = _load_criteria(agent_name)
    return [str(c.get("name", "")) for c in criteria if c.get("name")]


class EvaluatorNode:
    """Agentic node that evaluates upstream agent output.

    Returns accept (success), revise (failed with handoff feedback),
    or reject (failed with error).
    """

    @property
    def name(self) -> str:
        return "evaluator"

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Evaluate the current HTML against the original brief."""
        settings = get_settings()

        if not settings.ai.evaluator.enabled:
            return NodeResult(
                status="success",
                html=context.html,
                details="Evaluator disabled — passthrough",
            )

        brief = str(context.metadata.get("brief", context.brief or ""))
        upstream_agent = str(context.metadata.get("upstream_agent", "unknown"))
        criteria = _load_criteria_names(upstream_agent)

        try:
            service = get_evaluator_service()
            response = await service.evaluate(
                original_brief=brief,
                agent_name=upstream_agent,
                agent_output=context.html,
                quality_criteria=criteria,
                iteration=context.iteration,
            )
        except Exception as exc:
            logger.error(
                "blueprint.evaluator_node.failed",
                error=str(exc),
                upstream_agent=upstream_agent,
            )
            # Graceful degradation — pass through on evaluator failure
            return NodeResult(
                status="success",
                html=context.html,
                details=f"Evaluator error (passthrough): {exc}",
            )

        verdict = response.verdict

        if verdict.verdict == "accept":
            logger.info(
                "blueprint.evaluator_node.accepted",
                score=verdict.score,
                upstream_agent=upstream_agent,
            )
            return NodeResult(
                status="success",
                html=context.html,
                details=f"Evaluator accepted (score={verdict.score:.2f})",
            )

        if verdict.verdict == "reject":
            logger.info(
                "blueprint.evaluator_node.rejected",
                score=verdict.score,
                feedback=verdict.feedback[:200],
                upstream_agent=upstream_agent,
            )
            return NodeResult(
                status="failed",
                html=context.html,
                details=f"Evaluator rejected: {verdict.feedback}",
                error=verdict.feedback,
            )

        # "revise" — return failed with handoff containing feedback
        logger.info(
            "blueprint.evaluator_node.revise_requested",
            score=verdict.score,
            issue_count=len(verdict.issues),
            upstream_agent=upstream_agent,
        )
        return NodeResult(
            status="failed",
            html=context.html,
            details=f"Evaluator requests revision: {verdict.feedback}",
            handoff=AgentHandoff(
                agent_name="evaluator",
                artifact=context.html,
                status=HandoffStatus.WARNING,
                decisions=(verdict.feedback,),
                warnings=tuple(i.description for i in verdict.issues),
                component_refs=(),
                confidence=verdict.score,
            ),
        )
