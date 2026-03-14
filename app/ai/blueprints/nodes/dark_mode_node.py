# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
# ruff: noqa: ANN401
"""Dark Mode agentic node — enhances HTML with dark mode CSS and Outlook overrides."""

import json
from typing import Any

from app.ai.agents.dark_mode.prompt import build_system_prompt, detect_relevant_skills
from app.ai.agents.scaffolder.plan_merger import merge_dark_mode
from app.ai.agents.schemas.dark_mode_decisions import DarkColorOverride, DarkModeDecisions
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

        # Structured mode: return decisions instead of HTML
        if context.build_plan is not None:
            return await self._execute_structured(context, provider, model)

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

        if context.iteration > 0:
            structured: list[StructuredFailure] = context.metadata.get(  # type: ignore[assignment]
                "qa_failure_details", []
            )
            if structured:
                relevant = [f for f in structured if f.suggested_agent == "dark_mode"]
                other = [f for f in structured if f.suggested_agent != "dark_mode"]
                if relevant:
                    failure_lines = [
                        f"[P{f.priority}] {f.check_name} (score={f.score:.2f}): {f.details}"
                        for f in relevant
                    ]
                    parts.append(
                        "\n\n--- DARK MODE QA FAILURES (fix these — ordered by priority) ---\n"
                        + "\n".join(f"- {line}" for line in failure_lines)
                    )
                if other:
                    other_lines = [f"- {f.check_name}: {f.details}" for f in other[:3]]
                    parts.append(
                        "\n\n--- OTHER QA ISSUES (fix if possible without breaking your changes) ---\n"
                        + "\n".join(other_lines)
                    )
                scope_constraint = SCOPE_PROMPTS.get("dark_mode", "")
                if scope_constraint:
                    parts.append(f"\n\n--- MODIFICATION SCOPE ---\n{scope_constraint}")
            elif context.qa_failures:
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

        relevant_skills = detect_relevant_skills("")  # No HTML in structured mode
        system_prompt = build_system_prompt(relevant_skills, output_mode="structured")

        plan_summary = {
            "template": plan.template.template_name,
            "design_tokens": {
                "primary_color": plan.design_tokens.primary_color,
                "secondary_color": plan.design_tokens.secondary_color,
                "background_color": plan.design_tokens.background_color,
                "text_color": plan.design_tokens.text_color,
            },
            "dark_mode_strategy": plan.dark_mode_strategy,
        }

        user_message = (
            "Analyze this email build plan and return dark mode color decisions as JSON.\n\n"
            f"Plan: {json.dumps(plan_summary)}\n\n"
            "Return JSON with: color_overrides (array of {{token_name, light_value, dark_value, reasoning}}), "
            "background_dark, text_dark, enable_prefers_color_scheme, confidence, reasoning"
        )

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        try:
            response = await provider.complete(messages, model=model)
        except Exception as exc:
            logger.error("blueprint.dark_mode_node.structured_failed", error=str(exc))
            return NodeResult(status="failed", error=f"Structured dark mode failed: {exc}")

        # Parse decisions
        decisions = self._parse_decisions(response.content)

        # Merge into plan
        context.build_plan = merge_dark_mode(plan, decisions)

        usage = dict(response.usage) if response.usage else None

        handoff = AgentHandoff(
            agent_name="dark_mode",
            artifact="",  # No HTML artifact in structured mode
            decisions=(
                f"Dark mode decisions: {len(decisions.color_overrides)} overrides",
                f"Strategy: {'custom' if decisions.color_overrides else 'auto'}",
            ),
            warnings=(),
            confidence=decisions.confidence,
        )

        logger.info(
            "blueprint.dark_mode_node.structured_completed",
            overrides=len(decisions.color_overrides),
            confidence=decisions.confidence,
        )

        return NodeResult(
            status="success",
            html=context.html,  # Pass through existing HTML
            details=f"Dark mode decisions: {len(decisions.color_overrides)} overrides",
            usage=usage,
            handoff=handoff,
        )

    def _parse_decisions(self, raw_content: str) -> DarkModeDecisions:
        """Parse LLM response into DarkModeDecisions."""

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
            logger.warning("blueprint.dark_mode_node.parse_failed")
            return DarkModeDecisions(confidence=0.0, reasoning="Parse failed")

        overrides = tuple(
            DarkColorOverride(
                token_name=str(o.get("token_name", "")),
                light_value=str(o.get("light_value", "")),
                dark_value=str(o.get("dark_value", "")),
                reasoning=str(o.get("reasoning", "")),
            )
            for o in data.get("color_overrides", [])
            if isinstance(o, dict)
        )

        return DarkModeDecisions(
            color_overrides=overrides,
            background_dark=str(data.get("background_dark", "#1a1a2e")),
            text_dark=str(data.get("text_dark", "#e0e0e0")),
            enable_prefers_color_scheme=bool(data.get("enable_prefers_color_scheme", True)),
            confidence=float(data.get("confidence", 0.0)),
            reasoning=str(data.get("reasoning", "")),
        )
