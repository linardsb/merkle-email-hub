# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
# ruff: noqa: ANN401
"""Personalisation agentic node -- injects ESP dynamic content into email HTML."""

import json
from typing import Any

from app.ai.agents.html_summarizer import prepare_html_context
from app.ai.agents.personalisation.prompt import (
    build_system_prompt,
    detect_relevant_skills,
)
from app.ai.agents.personalisation.schemas import ESPPlatform
from app.ai.agents.personalisation.service import format_syntax_warnings
from app.ai.agents.scaffolder.plan_merger import merge_personalisation
from app.ai.agents.schemas.personalisation_decisions import (
    PersonalisationDecisions,
    VariablePlacement,
)
from app.ai.blueprints.component_context import detect_component_refs
from app.ai.blueprints.handoff import PersonalisationHandoff
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

        # Structured mode: return decisions instead of HTML
        if context.build_plan is not None:
            return await self._execute_structured(context, provider, model, platform, requirements)

        # Progressive disclosure: detect which skills are relevant
        client_id: str | None = context.metadata.get("client_id")  # type: ignore[assignment]
        relevant_skills = detect_relevant_skills(platform, requirements)
        system_prompt = build_system_prompt(relevant_skills, client_id=client_id)

        user_content = self._build_user_message(context, platform, requirements)
        sanitized = sanitize_prompt(user_content)

        cache_hint = {"type": "ephemeral"} if context.iteration > 0 else None
        messages = [
            Message(role="system", content=system_prompt, cache_control=cache_hint),
            Message(role="user", content=sanitized),
        ]

        try:
            response = await provider.complete(messages, model_override=model)
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

        # Validate personalisation syntax
        syntax_warnings = format_syntax_warnings(html)
        if syntax_warnings:
            logger.warning(
                "blueprint.personalisation_node.syntax_issues",
                issue_count=len(syntax_warnings),
                platform=platform,
            )

        usage = dict(response.usage) if response.usage else None

        typed = PersonalisationHandoff(platform=platform)

        handoff = AgentHandoff(
            agent_name="personalisation",
            artifact=html,
            decisions=(
                f"Injected {platform} personalisation into {len(html)} chars",
                f"Skills loaded: {', '.join(relevant_skills)}",
            ),
            warnings=tuple(syntax_warnings),
            component_refs=tuple(detect_component_refs(html)),
            confidence=confidence,
            typed_payload=typed,
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
            + prepare_html_context(context.html)
        ]

        if requirements:
            parts.append(f"\n\nPersonalisation requirements:\n{requirements}")

        if context.iteration > 0:
            structured: list[StructuredFailure] = context.metadata.get(  # type: ignore[assignment]
                "qa_failure_details", []
            )
            if structured:
                relevant = [f for f in structured if f.suggested_agent == "personalisation"]
                other = [f for f in structured if f.suggested_agent != "personalisation"]
                if relevant:
                    failure_lines = [
                        f"[P{f.priority}] {f.check_name} (score={f.score:.2f}): {f.details}"
                        for f in relevant
                    ]
                    parts.append(
                        "\n\n--- PERSONALISATION QA FAILURES (fix these — ordered by priority) ---\n"
                        + "\n".join(f"- {line}" for line in failure_lines)
                    )
                if other:
                    other_lines = [f"- {f.check_name}: {f.details}" for f in other[:3]]
                    parts.append(
                        "\n\n--- OTHER QA ISSUES (fix if possible without breaking your changes) ---\n"
                        + "\n".join(other_lines)
                    )
                scope_constraint = SCOPE_PROMPTS.get("personalisation", "")
                if scope_constraint:
                    parts.append(f"\n\n--- MODIFICATION SCOPE ---\n{scope_constraint}")
            elif context.qa_failures:
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
        platform: ESPPlatform,
        requirements: str,
    ) -> NodeResult:
        """Execute in structured mode: analyze plan, return decisions, merge."""
        plan = context.build_plan
        assert plan is not None  # noqa: S101

        client_id: str | None = context.metadata.get("client_id")  # type: ignore[assignment]
        relevant_skills = detect_relevant_skills(platform, requirements)
        system_prompt = build_system_prompt(
            relevant_skills, output_mode="structured", client_id=client_id
        )

        personalisable_slots = [
            {
                "slot_id": sf.slot_id,
                "content": sf.content[:200],
                "is_personalisable": sf.is_personalisable,
            }
            for sf in plan.slot_fills
        ]

        user_message = (
            f"Analyze this email build plan for {platform} personalisation.\n\n"
            f"Slots: {json.dumps(personalisable_slots)}\n\n"
            f"Requirements: {requirements}\n\n"
            "Return JSON with: esp_platform, variables (array of {{slot_id, variable_name, fallback_value, syntax}}), "
            "conditional_blocks, confidence, reasoning"
        )

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        try:
            response = await provider.complete(messages, model_override=model)
        except Exception as exc:
            logger.error("blueprint.personalisation_node.structured_failed", error=str(exc))
            return NodeResult(status="failed", error=f"Structured personalisation failed: {exc}")

        decisions = self._parse_decisions(response.content)
        context.build_plan = merge_personalisation(plan, decisions)

        usage = dict(response.usage) if response.usage else None

        typed = PersonalisationHandoff(
            platform=platform,
            merge_tags_added=len(decisions.variables),
            conditional_blocks=len(decisions.conditional_blocks),
        )

        handoff = AgentHandoff(
            agent_name="personalisation",
            artifact="",
            decisions=(
                f"Personalisation decisions: {len(decisions.variables)} variables for {platform}",
            ),
            warnings=(),
            confidence=decisions.confidence,
            typed_payload=typed,
        )

        logger.info(
            "blueprint.personalisation_node.structured_completed",
            platform=platform,
            variables=len(decisions.variables),
            confidence=decisions.confidence,
        )

        return NodeResult(
            status="success",
            html=context.html,
            details=f"Personalisation ({platform}): {len(decisions.variables)} variables",
            usage=usage,
            handoff=handoff,
        )

    def _parse_decisions(self, raw_content: str) -> PersonalisationDecisions:
        """Parse LLM response into PersonalisationDecisions."""
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
            logger.warning("blueprint.personalisation_node.parse_failed")
            return PersonalisationDecisions(confidence=0.0, reasoning="Parse failed")

        variables = tuple(
            VariablePlacement(
                slot_id=str(v.get("slot_id", "")),
                variable_name=str(v.get("variable_name", "")),
                fallback_value=str(v.get("fallback_value", "")),
                syntax=str(v.get("syntax", "")),
            )
            for v in data.get("variables", [])
            if isinstance(v, dict)
        )

        return PersonalisationDecisions(
            esp_platform=str(data.get("esp_platform", "")),
            variables=variables,
            conditional_blocks=tuple(str(c) for c in data.get("conditional_blocks", [])),
            confidence=float(data.get("confidence", 0.0)),
            reasoning=str(data.get("reasoning", "")),
        )
