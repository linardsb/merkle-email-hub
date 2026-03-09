"""Outlook Fixer agentic node — fixes Outlook rendering issues in email HTML."""

from app.ai.agents.outlook_fixer.prompt import (
    build_system_prompt,
    detect_relevant_skills,
)
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


class OutlookFixerNode:
    """Agentic node that fixes Outlook rendering issues in existing HTML.

    Receives context.html (email with Outlook issues) from recovery router.
    Uses progressive disclosure to load only relevant skill files.
    On retry: injects Outlook-specific QA failures into the prompt.
    """

    @property
    def name(self) -> str:
        return "outlook_fixer"

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Fix Outlook issues in HTML via LLM with progressive skill loading."""
        settings = get_settings()
        provider = get_registry().get_llm(settings.ai.provider)
        model = resolve_model("standard")

        # Progressive disclosure: detect which skills are relevant
        relevant_skills = detect_relevant_skills(context.html)
        system_prompt = build_system_prompt(relevant_skills)

        user_content = self._build_user_message(context)
        sanitized = sanitize_prompt(user_content)

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitized),
        ]

        try:
            response = await provider.complete(messages, model=model)
        except Exception as exc:
            logger.error("blueprint.outlook_fixer_node.llm_failed", error=str(exc))
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
            agent_name="outlook_fixer",
            artifact=html,
            decisions=(
                f"Fixed Outlook issues in {len(html)} chars",
                f"Skills loaded: {', '.join(relevant_skills)}",
            ),
            warnings=(),
            component_refs=tuple(detect_component_refs(html)),
            confidence=confidence,
        )

        logger.info(
            "blueprint.outlook_fixer_node.completed",
            iteration=context.iteration,
            html_length=len(html),
            confidence=confidence,
            skills_loaded=relevant_skills,
        )

        return NodeResult(
            status="success",
            html=html,
            details=f"Outlook fixes applied to {len(html)} chars (iteration {context.iteration})",
            usage=usage,
            handoff=handoff,
        )

    def _build_user_message(self, context: NodeContext) -> str:
        """Build user prompt from existing HTML with optional retry context."""
        parts = [
            "Fix the following email HTML for Outlook desktop compatibility:\n\n"
            + context.html[:12000]
        ]

        if context.iteration > 0 and context.qa_failures:
            outlook_failures = [
                f
                for f in context.qa_failures
                if any(
                    kw in f.lower() for kw in ("fallback", "mso", "vml", "outlook", "conditional")
                )
            ]
            if outlook_failures:
                parts.append(
                    "\n\n--- OUTLOOK QA FAILURES (fix these) ---\n"
                    + "\n".join(f"- {f}" for f in outlook_failures)
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
