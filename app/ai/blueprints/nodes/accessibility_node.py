# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
# ruff: noqa: ANN401
"""Accessibility Auditor agentic node — fixes WCAG AA issues in email HTML."""

import json
from typing import Any

from app.ai.agents.accessibility.alt_text_validator import format_alt_text_warnings
from app.ai.agents.accessibility.prompt import (
    build_system_prompt,
    detect_relevant_skills,
)
from app.ai.agents.html_summarizer import prepare_html_context
from app.ai.agents.scaffolder.plan_merger import merge_accessibility
from app.ai.agents.schemas.accessibility_decisions import (
    AccessibilityDecisions,
    AltTextDecision,
    HeadingDecision,
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

logger = get_logger(__name__)


class AccessibilityNode:
    """Agentic node that audits and fixes accessibility issues in email HTML.

    Receives context.html from recovery router (when QA detects accessibility failures).
    Uses progressive disclosure to load only relevant skill files.
    On retry: injects accessibility-specific QA failures into the prompt.
    """

    @property
    def name(self) -> str:
        return "accessibility"

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Fix accessibility issues in HTML via LLM with progressive skill loading."""
        settings = get_settings()
        provider = get_registry().get_llm(settings.ai.provider)
        model = resolve_model("standard")

        # Structured mode: return decisions instead of HTML
        if context.build_plan is not None:
            return await self._execute_structured(context, provider, model)

        # Progressive disclosure: detect which skills are relevant
        relevant_skills = detect_relevant_skills(context.html)
        system_prompt = build_system_prompt(relevant_skills)

        user_content = self._build_user_message(context)
        sanitized = sanitize_prompt(user_content)

        cache_hint = {"type": "ephemeral"} if context.iteration > 0 else None
        messages = [
            Message(role="system", content=system_prompt, cache_control=cache_hint),
            Message(role="user", content=sanitized),
        ]

        try:
            response = await provider.complete(messages, model=model)
        except Exception as exc:
            logger.error("blueprint.accessibility_node.llm_failed", error=str(exc))
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

        alt_warnings = format_alt_text_warnings(html)

        handoff = AgentHandoff(
            agent_name="accessibility",
            artifact=html,
            decisions=(
                f"Fixed accessibility issues in {len(html)} chars",
                f"Skills loaded: {', '.join(relevant_skills)}",
            ),
            warnings=tuple(alt_warnings),
            component_refs=tuple(detect_component_refs(html)),
            confidence=confidence,
        )

        logger.info(
            "blueprint.accessibility_node.completed",
            iteration=context.iteration,
            html_length=len(html),
            confidence=confidence,
            skills_loaded=relevant_skills,
            alt_text_warnings=len(alt_warnings),
        )

        return NodeResult(
            status="success",
            html=html,
            details=f"Accessibility fixes applied to {len(html)} chars (iteration {context.iteration})",
            usage=usage,
            handoff=handoff,
        )

    def _build_user_message(self, context: NodeContext) -> str:
        """Build user prompt from existing HTML with optional retry context."""
        parts = [
            "Audit and fix the following email HTML for WCAG 2.1 AA accessibility:\n\n"
            + prepare_html_context(context.html)
        ]

        if context.iteration > 0:
            structured: list[StructuredFailure] = context.metadata.get(  # type: ignore[assignment]
                "qa_failure_details", []
            )
            if structured:
                relevant = [f for f in structured if f.suggested_agent == "accessibility"]
                other = [f for f in structured if f.suggested_agent != "accessibility"]
                if relevant:
                    failure_lines = [
                        f"[P{f.priority}] {f.check_name} (score={f.score:.2f}): {f.details}"
                        for f in relevant
                    ]
                    parts.append(
                        "\n\n--- ACCESSIBILITY QA FAILURES (fix these — ordered by priority) ---\n"
                        + "\n".join(f"- {line}" for line in failure_lines)
                    )
                if other:
                    other_lines = [f"- {f.check_name}: {f.details}" for f in other[:3]]
                    parts.append(
                        "\n\n--- OTHER QA ISSUES (fix if possible without breaking your changes) ---\n"
                        + "\n".join(other_lines)
                    )
                scope_constraint = SCOPE_PROMPTS.get("accessibility", "")
                if scope_constraint:
                    parts.append(f"\n\n--- MODIFICATION SCOPE ---\n{scope_constraint}")
            elif context.qa_failures:
                a11y_failures = [
                    f
                    for f in context.qa_failures
                    if any(
                        kw in f.lower()
                        for kw in (
                            "accessibility",
                            "alt",
                            "lang",
                            "role",
                            "contrast",
                            "heading",
                            "wcag",
                        )
                    )
                ]
                if a11y_failures:
                    parts.append(
                        "\n\n--- ACCESSIBILITY QA FAILURES (fix these) ---\n"
                        + "\n".join(f"- {f}" for f in a11y_failures)
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

    async def _execute_structured(
        self,
        context: NodeContext,
        provider: Any,
        model: str,
    ) -> NodeResult:
        """Execute in structured mode: analyze plan, return decisions, merge."""

        plan = context.build_plan
        assert plan is not None  # noqa: S101

        relevant_skills = detect_relevant_skills("")
        system_prompt = build_system_prompt(relevant_skills, output_mode="structured")

        slot_ids = [sf.slot_id for sf in plan.slot_fills]
        plan_summary = {
            "template": plan.template.template_name,
            "slot_ids": slot_ids,
            "slot_fills": [
                {"slot_id": sf.slot_id, "content": sf.content[:200]} for sf in plan.slot_fills
            ],
        }

        user_message = (
            "Analyze this email build plan and return accessibility decisions as JSON.\n\n"
            f"Plan: {json.dumps(plan_summary)}\n\n"
            "Return JSON with: alt_texts (array of {{slot_id, alt_text, is_decorative}}), "
            "heading_fixes (array of {{slot_id, current_level, recommended_level, reason}}), "
            "lang_attribute, confidence, reasoning"
        )

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        try:
            response = await provider.complete(messages, model=model)
        except Exception as exc:
            logger.error("blueprint.accessibility_node.structured_failed", error=str(exc))
            return NodeResult(status="failed", error=f"Structured accessibility failed: {exc}")

        decisions = self._parse_decisions(response.content)
        context.build_plan = merge_accessibility(plan, decisions)

        usage = dict(response.usage) if response.usage else None

        handoff = AgentHandoff(
            agent_name="accessibility",
            artifact="",
            decisions=(
                f"Accessibility decisions: {len(decisions.alt_texts)} alt texts, {len(decisions.heading_fixes)} heading fixes",
            ),
            warnings=(),
            confidence=decisions.confidence,
        )

        logger.info(
            "blueprint.accessibility_node.structured_completed",
            alt_texts=len(decisions.alt_texts),
            heading_fixes=len(decisions.heading_fixes),
            confidence=decisions.confidence,
        )

        return NodeResult(
            status="success",
            html=context.html,
            details=f"Accessibility decisions: {len(decisions.alt_texts)} alt texts",
            usage=usage,
            handoff=handoff,
        )

    def _parse_decisions(self, raw_content: str) -> AccessibilityDecisions:
        """Parse LLM response into AccessibilityDecisions."""

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
            logger.warning("blueprint.accessibility_node.parse_failed")
            return AccessibilityDecisions(confidence=0.0, reasoning="Parse failed")

        alt_texts = tuple(
            AltTextDecision(
                slot_id=str(a.get("slot_id", "")),
                alt_text=str(a.get("alt_text", "")),
                is_decorative=bool(a.get("is_decorative", False)),
            )
            for a in data.get("alt_texts", [])
            if isinstance(a, dict)
        )

        heading_fixes = tuple(
            HeadingDecision(
                slot_id=str(h.get("slot_id", "")),
                current_level=int(h.get("current_level", 1)),
                recommended_level=int(h.get("recommended_level", 1)),
                reason=str(h.get("reason", "")),
            )
            for h in data.get("heading_fixes", [])
            if isinstance(h, dict)
        )

        return AccessibilityDecisions(
            alt_texts=alt_texts,
            heading_fixes=heading_fixes,
            lang_attribute=str(data.get("lang_attribute", "en")),
            confidence=float(data.get("confidence", 0.0)),
            reasoning=str(data.get("reasoning", "")),
        )
