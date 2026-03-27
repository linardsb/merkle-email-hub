# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
# ruff: noqa: ANN401
"""Outlook Fixer agentic node — fixes Outlook rendering issues in email HTML."""

import json
from typing import Any

from app.ai.agents.html_summarizer import prepare_html_context
from app.ai.agents.outlook_fixer.mso_repair import repair_mso_issues
from app.ai.agents.outlook_fixer.prompt import (
    build_system_prompt,
    detect_relevant_skills,
)
from app.ai.agents.schemas.outlook_diagnostic import MSOIssue, OutlookDiagnostic
from app.ai.blueprints.component_context import detect_component_refs
from app.ai.blueprints.handoff import OutlookFixerHandoff
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

        # Structured mode: diagnostic-only
        if context.build_plan is not None:
            return await self._execute_structured(context, provider, model)

        # Progressive disclosure: detect which skills are relevant
        client_id: str | None = context.metadata.get("client_id")  # type: ignore[assignment]
        relevant_skills = detect_relevant_skills(context.html)
        system_prompt = build_system_prompt(relevant_skills, client_id=client_id)

        user_content = self._build_user_message(context)
        sanitized = sanitize_prompt(user_content)

        cache_hint = {"type": "ephemeral"} if context.iteration > 0 else None
        messages = [
            Message(role="system", content=system_prompt, cache_control=cache_hint),
            Message(role="user", content=sanitized),
        ]

        try:
            response = await provider.complete(messages, model_override=model)
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

        typed = OutlookFixerHandoff(
            issues_found=len(mso_result.issues),
            mso_conditionals_added=len(mso_warnings),
        )

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
            typed_payload=typed,
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

    async def _execute_structured(
        self,
        context: NodeContext,
        provider: Any,
        model: str,
    ) -> NodeResult:
        """Execute in diagnostic mode: report MSO issues without modifying HTML."""
        client_id: str | None = context.metadata.get("client_id")  # type: ignore[assignment]
        relevant_skills = detect_relevant_skills(context.html or "")
        system_prompt = build_system_prompt(
            relevant_skills, output_mode="structured", client_id=client_id
        )

        user_message = (
            "Analyze this assembled email HTML for MSO/Outlook compatibility issues. "
            "Report issues but do NOT fix — golden templates handle MSO.\n\n"
            f"HTML:\n{prepare_html_context(context.html)}\n\n"
            "Return JSON with: issues (array of {{issue_type, severity, location, recommendation}}), "
            "template_bug, composition_bug, overall_mso_safe, confidence, reasoning"
        )

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        try:
            response = await provider.complete(messages, model_override=model)
        except Exception as exc:
            logger.error("blueprint.outlook_fixer_node.diagnostic_failed", error=str(exc))
            return NodeResult(status="failed", error=f"Outlook diagnostic failed: {exc}")

        diagnostic = self._parse_diagnostic(response.content)

        usage = dict(response.usage) if response.usage else None

        warnings = tuple(
            f"MSO [{i.severity}] {i.issue_type}: {i.recommendation}" for i in diagnostic.issues
        )

        typed = OutlookFixerHandoff(
            issues_found=len(diagnostic.issues),
            severity_counts={},
        )

        handoff = AgentHandoff(
            agent_name="outlook_fixer",
            artifact=context.html,  # Pass through unchanged
            decisions=(
                f"Diagnostic: {len(diagnostic.issues)} MSO issues found",
                f"MSO safe: {diagnostic.overall_mso_safe}",
            ),
            warnings=warnings,
            confidence=diagnostic.confidence,
            typed_payload=typed,
        )

        logger.info(
            "blueprint.outlook_fixer_node.diagnostic_completed",
            issues=len(diagnostic.issues),
            mso_safe=diagnostic.overall_mso_safe,
            confidence=diagnostic.confidence,
        )

        return NodeResult(
            status="success",
            html=context.html,  # Unchanged
            details=f"Outlook diagnostic: {len(diagnostic.issues)} issues",
            usage=usage,
            handoff=handoff,
        )

    def _parse_diagnostic(self, raw_content: str) -> OutlookDiagnostic:
        """Parse LLM response into OutlookDiagnostic."""
        content = raw_content.strip()
        if "```json" in content:
            start = content.index("```json") + 7
            end = content.index("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.index("```") + 3
            end = content.index("```", start)
            content = content[start:end].strip()

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("blueprint.outlook_fixer_node.diagnostic_parse_failed")
            return OutlookDiagnostic(confidence=0.0, reasoning="Parse failed")

        issues = tuple(
            MSOIssue(
                issue_type=str(i.get("issue_type", "")),
                severity=i.get("severity", "info"),
                location=str(i.get("location", "")),
                recommendation=str(i.get("recommendation", "")),
            )
            for i in data.get("issues", [])
            if isinstance(i, dict)
        )

        return OutlookDiagnostic(
            issues=issues,
            template_bug=bool(data.get("template_bug", False)),
            composition_bug=bool(data.get("composition_bug", False)),
            overall_mso_safe=bool(data.get("overall_mso_safe", True)),
            confidence=float(data.get("confidence", 0.0)),
            reasoning=str(data.get("reasoning", "")),
        )

    def _build_user_message(self, context: NodeContext) -> str:
        """Build user prompt from existing HTML with optional retry context."""
        parts = [
            "Fix the following email HTML for Outlook desktop compatibility:\n\n"
            + prepare_html_context(context.html)
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
