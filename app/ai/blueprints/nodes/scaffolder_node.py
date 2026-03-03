"""Scaffolder agentic node — generates Maizzle HTML from campaign briefs."""

from app.ai.agents.scaffolder.prompt import SCAFFOLDER_SYSTEM_PROMPT
from app.ai.blueprints.protocols import NodeContext, NodeResult, NodeType
from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import extract_html, sanitize_html_xss
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ScaffolderNode:
    """Agentic node that generates email HTML from a campaign brief.

    On first call (iteration 0): standard brief → LLM → extract → sanitize.
    On retry (iteration > 0): injects QA failures + progress anchor into prompt.
    """

    @property
    def name(self) -> str:
        return "scaffolder"

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Generate or fix email HTML via LLM."""
        settings = get_settings()
        provider = get_registry().get_llm(settings.ai.provider)
        model = resolve_model("complex")

        user_content = self._build_user_message(context)
        sanitized = sanitize_prompt(user_content)

        messages = [
            Message(role="system", content=SCAFFOLDER_SYSTEM_PROMPT),
            Message(role="user", content=sanitized),
        ]

        try:
            response = await provider.complete(messages, model=model)
        except Exception as exc:
            logger.error("blueprint.scaffolder_node.llm_failed", error=str(exc))
            return NodeResult(
                status="failed",
                error=f"LLM call failed: {exc}",
            )

        validated = validate_output(response.content)
        html = extract_html(validated)
        html = sanitize_html_xss(html)

        usage = dict(response.usage) if response.usage else None

        logger.info(
            "blueprint.scaffolder_node.completed",
            iteration=context.iteration,
            html_length=len(html),
        )

        return NodeResult(
            status="success",
            html=html,
            details=f"Generated {len(html)} chars (iteration {context.iteration})",
            usage=usage,
        )

    def _build_user_message(self, context: NodeContext) -> str:
        """Build user prompt with brief and optional retry context."""
        if context.iteration == 0:
            return context.brief

        parts = [context.brief]

        if context.qa_failures:
            parts.append(
                "\n\n--- QA FAILURES (fix these) ---\n"
                + "\n".join(f"- {f}" for f in context.qa_failures)
            )

        progress = context.metadata.get("progress_anchor", "")
        if progress:
            parts.append(f"\n\n{progress}")

        if context.html:
            parts.append("\n\n--- PREVIOUS ATTEMPT (improve this) ---\n" + context.html[:8000])

        return "\n".join(parts)
