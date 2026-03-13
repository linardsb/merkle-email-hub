"""Outlook Fixer agentic node — fixes Outlook rendering issues in email HTML."""

from app.ai.agents.outlook_fixer.mso_repair import repair_mso_issues
from app.ai.agents.outlook_fixer.prompt import (
    build_system_prompt,
    detect_relevant_skills,
)
from app.ai.blueprints.component_context import detect_component_refs
from app.ai.blueprints.nodes.recovery_router_node import SCOPE_PROMPTS
from app.ai.blueprints.protocols import (
    AgentHandoff,
    NodeContext,
    NodeResult,
    NodeType,
    StructuredFailure,
)
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
from app.qa_engine.mso_parser import validate_mso_conditionals

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

        # Post-generation MSO validation + programmatic repair
        mso_result = validate_mso_conditionals(html)
        mso_warnings: tuple[str, ...] = ()

        if not mso_result.is_valid:
            html, repairs = repair_mso_issues(html, mso_result)

            # Re-validate
            post_repair = validate_mso_conditionals(html)
            if post_repair.is_valid:
                mso_warnings = tuple(f"MSO repaired: {r}" for r in repairs)
            else:
                mso_warnings = tuple(f"MSO: {issue.message}" for issue in post_repair.issues)

            logger.info(
                "blueprint.outlook_fixer_node.mso_validated",
                issues_before=len(mso_result.issues),
                issues_after=len(post_repair.issues),
                repairs_applied=len(repairs),
            )

        usage = dict(response.usage) if response.usage else None

        handoff = AgentHandoff(
            agent_name="outlook_fixer",
            artifact=html,
            decisions=(
                f"Fixed Outlook issues in {len(html)} chars",
                f"Skills loaded: {', '.join(relevant_skills)}",
            ),
            warnings=mso_warnings,
            component_refs=tuple(detect_component_refs(html)),
            confidence=confidence,
        )

        logger.info(
            "blueprint.outlook_fixer_node.completed",
            iteration=context.iteration,
            html_length=len(html),
            confidence=confidence,
            skills_loaded=relevant_skills,
            mso_warnings=len(mso_warnings),
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

        if context.iteration > 0:
            structured: list[StructuredFailure] = context.metadata.get(  # type: ignore[assignment]
                "qa_failure_details", []
            )
            if structured:
                relevant = [f for f in structured if f.suggested_agent == "outlook_fixer"]
                other = [f for f in structured if f.suggested_agent != "outlook_fixer"]
                if relevant:
                    failure_lines = [
                        f"[P{f.priority}] {f.check_name} (score={f.score:.2f}): {f.details}"
                        for f in relevant
                    ]
                    parts.append(
                        "\n\n--- OUTLOOK QA FAILURES (fix these — ordered by priority) ---\n"
                        + "\n".join(f"- {line}" for line in failure_lines)
                    )
                if other:
                    other_lines = [f"- {f.check_name}: {f.details}" for f in other[:3]]
                    parts.append(
                        "\n\n--- OTHER QA ISSUES (fix if possible without breaking your changes) ---\n"
                        + "\n".join(other_lines)
                    )
                scope_constraint = SCOPE_PROMPTS.get("outlook_fixer", "")
                if scope_constraint:
                    parts.append(f"\n\n--- MODIFICATION SCOPE ---\n{scope_constraint}")
            elif context.qa_failures:
                outlook_failures = [
                    f
                    for f in context.qa_failures
                    if any(
                        kw in f.lower()
                        for kw in ("fallback", "mso", "vml", "outlook", "conditional")
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
        audience_ctx = context.metadata.get("audience_context", "")
        if audience_ctx:
            parts.append(f"\n\n{audience_ctx}")
        graph_ctx = context.metadata.get("graph_context", "")
        if graph_ctx:
            parts.append(f"\n\n{graph_ctx}")

        return "\n".join(parts)
