# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
"""Innovation node — experimental technique prototyping for blueprint context.

Advisory node: provides technique feasibility assessment to downstream agents.
Not part of the QA → recovery router loop.
"""

from app.ai.agents.innovation.prompt import build_system_prompt, detect_relevant_skills
from app.ai.blueprints.handoff import InnovationHandoff
from app.ai.blueprints.protocols import (
    AgentHandoff,
    HandoffStatus,
    NodeContext,
    NodeResult,
    NodeType,
)
from app.ai.protocols import CompletionResponse, Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import extract_confidence, strip_confidence_comment
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class InnovationNode:
    """Advisory blueprint node for experimental technique prototyping."""

    @property
    def name(self) -> str:
        return "innovation"

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Execute innovation prototyping for the current brief/context.

        Reads the brief as the technique request. Returns prototype and
        feasibility in AgentHandoff.decisions for downstream agents.
        """
        settings = get_settings()
        registry = get_registry()
        provider = registry.get_llm(settings.ai.provider)
        model = resolve_model("complex")

        technique = context.brief or context.metadata.get("innovation_request", "")
        if not technique:
            return NodeResult(
                status="skipped",
                html=context.html,
                details="No technique request provided for innovation prototyping",
            )

        # Build prompt
        client_id: str | None = context.metadata.get("client_id")  # type: ignore[assignment]
        relevant_skills = detect_relevant_skills(str(technique))
        system_prompt = build_system_prompt(relevant_skills, client_id=client_id)

        graph_ctx = context.metadata.get("graph_context", "")
        graph_section = f"\n\n{graph_ctx}" if graph_ctx else ""

        competitive_ctx = context.metadata.get("competitive_context", "")
        competitive_section = f"\n\n{competitive_ctx}" if competitive_ctx else ""

        user_message = (
            f"## TECHNIQUE REQUEST\n{technique}"
            f"{graph_section}{competitive_section}\n\n"
            "Provide a working prototype, feasibility assessment with client coverage %, "
            "risk level, and recommendation, plus a static fallback.\n"
            "End with <!-- CONFIDENCE: 0.XX -->"
        )

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        try:
            response: CompletionResponse = await provider.complete(messages, model_override=model)
        except Exception as exc:
            logger.error("agents.innovation.node_failed", error=str(exc))
            return NodeResult(
                status="failed",
                html=context.html,
                error=f"Innovation prototyping failed: {exc}",
            )

        raw_output = validate_output(response.content)
        confidence = extract_confidence(raw_output)
        clean_output = strip_confidence_comment(raw_output)

        typed = InnovationHandoff(
            technique=str(technique)[:100],
            feasibility_score=confidence or 0.0,
        )

        handoff = AgentHandoff(
            status=HandoffStatus.OK,
            agent_name="innovation",
            artifact=clean_output,
            decisions=(f"innovation_prototype: {clean_output[:200]}",),
            warnings=(),
            component_refs=(),
            confidence=confidence,
            typed_payload=typed,
        )

        return NodeResult(
            status="success",
            html=context.html,  # Pass through unchanged
            handoff=handoff,
            usage=response.usage,
        )
