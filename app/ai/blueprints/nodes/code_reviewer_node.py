# pyright: reportUnknownMemberType=false
"""Code Reviewer agentic node -- analyses email HTML and reports issues."""

import json
from typing import Any

from app.ai.agents.code_reviewer.actionability import detect_responsible_agent
from app.ai.agents.code_reviewer.prompt import (
    build_system_prompt,
    detect_relevant_skills,
)
from app.ai.agents.code_reviewer.schemas import CodeReviewIssue, ReviewFocus
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
from app.ai.shared import extract_confidence, strip_confidence_comment
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _detect_agent_from_item(item: dict[str, Any]) -> str:
    """Detect responsible agent from a raw issue dict."""
    issue = CodeReviewIssue(
        rule=str(item.get("rule", "unknown")),
        severity=item.get("severity", "info"),
        message=str(item.get("message", "")),
        suggestion=item.get("suggestion"),
    )
    return detect_responsible_agent(issue)


class CodeReviewerNode:
    """Agentic node that reviews email HTML for issues.

    Receives context.html (email) + optional review focus from metadata.
    On retry: injects code-review-related QA failures into the prompt.
    Unlike other nodes, passes HTML through unchanged — issues go into handoff warnings.
    """

    @property
    def name(self) -> str:
        return "code_reviewer"

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Review email HTML via LLM and return issues as handoff warnings."""
        settings = get_settings()
        provider = get_registry().get_llm(settings.ai.provider)
        model = resolve_model("standard")

        # Read focus from metadata (default to "all")
        focus: ReviewFocus = context.metadata.get("review_focus", "all")  # type: ignore[assignment]

        # Progressive disclosure: detect which skills are relevant
        relevant_skills = detect_relevant_skills(focus)
        system_prompt = build_system_prompt(relevant_skills)

        user_content = self._build_user_message(context, focus)
        sanitized = sanitize_prompt(user_content)

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitized),
        ]

        try:
            response = await provider.complete(messages, model=model)
        except Exception as exc:
            logger.error("blueprint.code_reviewer_node.llm_failed", error=str(exc))
            return NodeResult(
                status="failed",
                error=f"LLM call failed: {exc}",
            )

        validated = validate_output(response.content)
        confidence = extract_confidence(validated)
        clean_content = strip_confidence_comment(validated)

        # Parse issues from response
        issues_as_warnings: tuple[str, ...] = ()
        try:
            # Extract JSON from code fence
            content = clean_content
            if "```json" in content:
                start = content.index("```json") + 7
                end = content.index("```", start)
                content = content[start:end].strip()

            data = json.loads(content)
            raw_issues = data.get("issues", [])
            issues_as_warnings = tuple(
                f"code_review: [{item.get('severity', 'info')}] {item.get('rule', 'unknown')}: "
                f"{item.get('message', '')}"
                f" | agent={_detect_agent_from_item(item)}"  # pyright: ignore[reportUnknownArgumentType]
                for item in raw_issues
                if isinstance(item, dict)
            )
        except (json.JSONDecodeError, ValueError):
            issues_as_warnings = (f"code_review: raw output: {clean_content[:200]}",)

        usage = dict(response.usage) if response.usage else None

        # Code reviewer passes HTML through unchanged; issues go into warnings
        handoff = AgentHandoff(
            agent_name="code_reviewer",
            artifact=context.html,  # HTML unchanged
            decisions=(
                f"Reviewed {len(context.html)} chars with focus={focus}",
                f"Found {len(issues_as_warnings)} issue(s)",
                f"Skills loaded: {', '.join(relevant_skills)}",
            ),
            warnings=issues_as_warnings,
            component_refs=tuple(detect_component_refs(context.html)),
            confidence=confidence,
        )

        logger.info(
            "blueprint.code_reviewer_node.completed",
            iteration=context.iteration,
            focus=focus,
            issue_count=len(issues_as_warnings),
            confidence=confidence,
            skills_loaded=relevant_skills,
        )

        return NodeResult(
            status="success",
            html=context.html,  # Pass through unchanged
            details=f"Code review completed: {len(issues_as_warnings)} issue(s) found (iteration {context.iteration})",
            usage=usage,
            handoff=handoff,
        )

    def _build_user_message(self, context: NodeContext, focus: ReviewFocus) -> str:
        """Build user prompt from existing HTML with optional retry context."""
        focus_label = "all areas" if focus == "all" else focus
        parts = [
            f"Review the following email HTML. Focus on: {focus_label}.\n\n" + context.html[:12000]
        ]

        if context.iteration > 0:
            structured: list[StructuredFailure] = context.metadata.get(  # type: ignore[assignment]
                "qa_failure_details", []
            )
            if structured:
                relevant = [f for f in structured if f.suggested_agent == "code_reviewer"]
                other = [f for f in structured if f.suggested_agent != "code_reviewer"]
                if relevant:
                    failure_lines = [
                        f"[P{f.priority}] {f.check_name} (score={f.score:.2f}): {f.details}"
                        for f in relevant
                    ]
                    parts.append(
                        "\n\n--- CODE REVIEW QA FAILURES (address these — ordered by priority) ---\n"
                        + "\n".join(f"- {line}" for line in failure_lines)
                    )
                if other:
                    other_lines = [f"- {f.check_name}: {f.details}" for f in other[:3]]
                    parts.append(
                        "\n\n--- OTHER QA ISSUES (fix if possible without breaking your changes) ---\n"
                        + "\n".join(other_lines)
                    )
                scope_constraint = SCOPE_PROMPTS.get("code_reviewer", "")
                if scope_constraint:
                    parts.append(f"\n\n--- MODIFICATION SCOPE ---\n{scope_constraint}")
            elif context.qa_failures:
                relevant_failures = [
                    f
                    for f in context.qa_failures
                    if any(
                        kw in f.lower()
                        for kw in (
                            "code_review",
                            "redundant",
                            "css_support",
                            "nesting",
                            "file_size",
                            "unsupported",
                        )
                    )
                ]
                if relevant_failures:
                    parts.append(
                        "\n\n--- CODE REVIEW QA FAILURES (address these) ---\n"
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
        audience_ctx = context.metadata.get("audience_context", "")
        if audience_ctx:
            parts.append(f"\n\n{audience_ctx}")
        graph_ctx = context.metadata.get("graph_context", "")
        if graph_ctx:
            parts.append(f"\n\n{graph_ctx}")

        return "\n".join(parts)
