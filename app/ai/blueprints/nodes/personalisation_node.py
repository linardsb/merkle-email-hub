"""Personalisation agentic node -- injects ESP dynamic content into email HTML."""

from app.ai.agents.personalisation.prompt import (
    build_system_prompt,
    detect_relevant_skills,
)
from app.ai.agents.personalisation.schemas import ESPPlatform
from app.ai.blueprints.component_context import detect_component_refs
from app.ai.blueprints.protocols import AgentHandoff, NodeContext, NodeResult, NodeType
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import (
    extract_confidence,
    extract_html,
    sanitize_html_xss,
    strip_confidence_comment,
)
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class PersonalisationNode:
    """Agentic node that injects ESP personalisation syntax into email HTML.

    Receives context.html (email) + platform/requirements from metadata.
    Uses progressive disclosure to load only the platform-specific skill file.
    On retry: injects personalisation-related QA failures into the prompt.
    """

    @property
    def name(self) -> str:
        return "personalisation"

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Inject ESP personalisation via LLM with progressive skill loading."""
        settings = get_settings()
        provider = get_registry().get_llm(settings.ai.provider)
        model = resolve_model("standard")

        # Read platform from metadata (default to braze if not specified)
        platform: ESPPlatform = context.metadata.get("esp_platform", "braze")  # type: ignore[assignment]
        requirements: str = str(context.metadata.get("personalisation_requirements", ""))

        # Progressive disclosure: detect which skills are relevant
        relevant_skills = detect_relevant_skills(platform, requirements)
        system_prompt = build_system_prompt(relevant_skills)

        user_content = self._build_user_message(context, platform, requirements)
        sanitized = sanitize_prompt(user_content)

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitized),
        ]

        try:
            response = await provider.complete(messages, model=model)
        except Exception as exc:
            logger.error("blueprint.personalisation_node.llm_failed", error=str(exc))
            return NodeResult(
                status="failed",
                error=f"LLM call failed: {exc}",
            )

        validated = validate_output(response.content)
        html = extract_html(validated)
        confidence = extract_confidence(html)
        html = strip_confidence_comment(html)
        html = sanitize_html_xss(html)

        usage = dict(response.usage) if response.usage else None

        handoff = AgentHandoff(
            agent_name="personalisation",
            artifact=html,
            decisions=(
                f"Injected {platform} personalisation into {len(html)} chars",
                f"Skills loaded: {', '.join(relevant_skills)}",
            ),
            warnings=(),
            component_refs=tuple(detect_component_refs(html)),
            confidence=confidence,
        )

        logger.info(
            "blueprint.personalisation_node.completed",
            iteration=context.iteration,
            platform=platform,
            html_length=len(html),
            confidence=confidence,
            skills_loaded=relevant_skills,
        )

        return NodeResult(
            status="success",
            html=html,
            details=f"Personalisation ({platform}) applied to {len(html)} chars (iteration {context.iteration})",
            usage=usage,
            handoff=handoff,
        )

    def _build_user_message(
        self, context: NodeContext, platform: ESPPlatform, requirements: str
    ) -> str:
        """Build user prompt from existing HTML with optional retry context."""
        parts = [
            f"Add {platform} personalisation to the following email HTML:\n\n"
            + context.html[:12000]
        ]

        if requirements:
            parts.append(f"\n\nPersonalisation requirements:\n{requirements}")

        if context.iteration > 0 and context.qa_failures:
            relevant_failures = [
                f
                for f in context.qa_failures
                if any(
                    kw in f.lower()
                    for kw in (
                        "personalisation",
                        "personalization",
                        "liquid",
                        "ampscript",
                        "variable",
                        "fallback",
                        "dynamic",
                        "tag",
                    )
                )
            ]
            if relevant_failures:
                parts.append(
                    "\n\n--- PERSONALISATION QA FAILURES (fix these) ---\n"
                    + "\n".join(f"- {f}" for f in relevant_failures)
                )

        # Read upstream handoff warnings
        upstream = context.metadata.get("upstream_handoff")
        if isinstance(upstream, AgentHandoff) and upstream.warnings:
            parts.append(
                "\n\n--- UPSTREAM WARNINGS ---\n" + "\n".join(f"- {w}" for w in upstream.warnings)
            )

        component_ctx = context.metadata.get("component_context", "")
        if component_ctx:
            parts.append(f"\n\n{component_ctx}")
        graph_ctx = context.metadata.get("graph_context", "")
        if graph_ctx:
            parts.append(f"\n\n{graph_ctx}")

        return "\n".join(parts)
