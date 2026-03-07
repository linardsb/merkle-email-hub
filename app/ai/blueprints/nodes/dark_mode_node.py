"""Dark Mode agentic node — enhances HTML with dark mode CSS and Outlook overrides."""

from app.ai.agents.dark_mode.prompt import DARK_MODE_SYSTEM_PROMPT
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


class DarkModeNode:
    """Agentic node that injects dark mode support into existing HTML.

    Receives context.html (existing email to enhance), NOT a brief.
    On retry: injects dark-mode-specific QA failures into the prompt.
    """

    @property
    def name(self) -> str:
        return "dark_mode"

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Enhance HTML with dark mode via LLM."""
        settings = get_settings()
        provider = get_registry().get_llm(settings.ai.provider)
        model = resolve_model("standard")

        user_content = self._build_user_message(context)
        sanitized = sanitize_prompt(user_content)

        messages = [
            Message(role="system", content=DARK_MODE_SYSTEM_PROMPT),
            Message(role="user", content=sanitized),
        ]

        try:
            response = await provider.complete(messages, model=model)
        except Exception as exc:
            logger.error("blueprint.dark_mode_node.llm_failed", error=str(exc))
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
            agent_name="dark_mode",
            artifact=html,
            decisions=(f"Dark mode enhanced {len(html)} chars",),
            warnings=(),
            component_refs=tuple(detect_component_refs(html)),
            confidence=confidence,
        )

        logger.info(
            "blueprint.dark_mode_node.completed",
            iteration=context.iteration,
            html_length=len(html),
            confidence=confidence,
        )

        return NodeResult(
            status="success",
            html=html,
            details=f"Dark mode enhanced {len(html)} chars (iteration {context.iteration})",
            usage=usage,
            handoff=handoff,
        )

    def _build_user_message(self, context: NodeContext) -> str:
        """Build user prompt from existing HTML with optional retry context."""
        parts = [
            "Enhance the following email HTML with dark mode support:\n\n" + context.html[:12000]
        ]

        if context.iteration > 0 and context.qa_failures:
            dm_failures = [f for f in context.qa_failures if "dark_mode" in f.lower()]
            if dm_failures:
                parts.append(
                    "\n\n--- DARK MODE QA FAILURES (fix these) ---\n"
                    + "\n".join(f"- {f}" for f in dm_failures)
                )

        progress = context.metadata.get("progress_anchor", "")
        if progress:
            parts.append(f"\n\n{progress}")

        # Read upstream handoff warnings
        upstream = context.metadata.get("upstream_handoff")
        if isinstance(upstream, AgentHandoff) and upstream.warnings:
            parts.append(
                "\n\n--- UPSTREAM WARNINGS ---\n" + "\n".join(f"- {w}" for w in upstream.warnings)
            )

        component_ctx = context.metadata.get("component_context", "")
        if component_ctx:
            parts.append(f"\n\n{component_ctx}")

        return "\n".join(parts)
