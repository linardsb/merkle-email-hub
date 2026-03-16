"""Scaffolder agentic node — generates Maizzle HTML from campaign briefs."""

from app.ai.agents.scaffolder.prompt import build_system_prompt, detect_relevant_skills
from app.ai.blueprints.component_context import detect_component_refs
from app.ai.blueprints.handoff import ScaffolderHandoff
from app.ai.blueprints.nodes.recovery_router_node import SCOPE_PROMPTS
from app.ai.blueprints.protocols import (
    AgentHandoff,
    NodeContext,
    NodeResult,
    NodeType,
    StructuredFailure,
)
from app.ai.protocols import LLMProvider, Message
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

        # Structured mode: 3-pass pipeline + deterministic assembly
        output_mode = context.metadata.get("output_mode", "html")
        if output_mode == "structured":
            return await self._execute_structured(context, provider, model)

        relevant_skills = detect_relevant_skills(context.brief)
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
            logger.error("blueprint.scaffolder_node.llm_failed", error=str(exc))
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

        # MSO-first: validate generated HTML for Outlook issues
        mso_result = validate_mso_conditionals(html)
        mso_warnings = tuple(
            f"[{issue.severity}] {issue.category}: {issue.message}" for issue in mso_result.issues
        )

        if mso_warnings:
            logger.warning(
                "blueprint.scaffolder_node.mso_issues",
                issue_count=len(mso_warnings),
            )

        typed = ScaffolderHandoff(
            template_name="generated",
            design_token_source="brief",  # noqa: S106
        )

        handoff = AgentHandoff(
            agent_name="scaffolder",
            artifact=html,
            decisions=(f"Generated {len(html)} chars from brief",),
            warnings=mso_warnings,
            component_refs=tuple(detect_component_refs(html)),
            confidence=confidence,
            typed_payload=typed,
        )

        logger.info(
            "blueprint.scaffolder_node.completed",
            iteration=context.iteration,
            html_length=len(html),
            confidence=confidence,
        )

        return NodeResult(
            status="success",
            html=html,
            details=f"Generated {len(html)} chars (iteration {context.iteration})",
            usage=usage,
            handoff=handoff,
        )

    async def _execute_structured(
        self,
        context: NodeContext,
        provider: LLMProvider,
        model: str,
    ) -> NodeResult:
        """Execute using 3-pass pipeline + deterministic assembly."""
        from app.ai.agents.scaffolder.assembler import TemplateAssembler
        from app.ai.agents.scaffolder.pipeline import ScaffolderPipeline

        design_system = context.metadata.get("design_system")

        # Wire pipeline checkpoint callback from engine context
        checkpoint_cb = context.metadata.get("pipeline_checkpoint_cb")
        run_id = context.metadata.get("run_id", "")

        pipeline = ScaffolderPipeline(
            provider,
            model,
            design_system=design_system,  # type: ignore[arg-type]
            checkpoint_callback=checkpoint_cb,  # type: ignore[arg-type]
            run_id=run_id,  # type: ignore[arg-type]
        )

        # Resume from checkpoint on retry iterations
        resume = context.iteration > 0 and checkpoint_cb is not None

        try:
            plan = await pipeline.execute(context.brief, resume=resume)
        except Exception as exc:
            logger.error("blueprint.scaffolder_node.pipeline_failed", error=str(exc))
            return NodeResult(status="failed", error=f"Pipeline failed: {exc}")

        # Store plan in context for downstream agents
        context.build_plan = plan

        assembler = TemplateAssembler(design_system=design_system)  # type: ignore[arg-type]
        try:
            html = assembler.assemble(plan)
        except Exception as exc:
            logger.error("blueprint.scaffolder_node.assembly_failed", error=str(exc))
            return NodeResult(status="failed", error=f"Assembly failed: {exc}")

        html = sanitize_html_xss(html)

        typed = ScaffolderHandoff(
            template_name=plan.template.template_name,
            slots_filled=tuple(sf.slot_id for sf in plan.slot_fills),
            design_token_source=plan.design_tokens.source,
            colors_applied=dict(plan.design_tokens.colors) if plan.design_tokens.colors else {},
            locked_roles=tuple(plan.design_tokens.locked_roles)
            if plan.design_tokens.locked_roles
            else (),
            dark_mode_strategy=plan.dark_mode_strategy or "",
        )

        handoff = AgentHandoff(
            agent_name="scaffolder",
            artifact=html,
            decisions=(
                f"Template: {plan.template.template_name}",
                f"Slots filled: {len(plan.slot_fills)}",
                f"Design: {plan.design_tokens.source} ({len(plan.design_tokens.colors)} colors)",
                f"Locked: {len(plan.design_tokens.locked_roles)} roles",
            ),
            warnings=(),
            component_refs=tuple(detect_component_refs(html)),
            confidence=plan.confidence,
            typed_payload=typed,
        )

        return NodeResult(
            status="success",
            html=html,
            details=f"Structured pipeline: {plan.template.template_name}, {len(plan.slot_fills)} slots",
            handoff=handoff,
        )

    def _build_user_message(self, context: NodeContext) -> str:
        """Build user prompt with brief and optional retry context."""
        if context.iteration == 0:
            parts = [context.brief]
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

        parts = [context.brief]

        structured: list[StructuredFailure] = context.metadata.get(  # type: ignore[assignment]
            "qa_failure_details", []
        )
        if structured:
            relevant = [f for f in structured if f.suggested_agent == "scaffolder"]
            other = [f for f in structured if f.suggested_agent != "scaffolder"]
            if relevant:
                failure_lines = [
                    f"[P{f.priority}] {f.check_name} (score={f.score:.2f}): {f.details}"
                    for f in relevant
                ]
                parts.append(
                    "\n\n--- QA FAILURES (fix these — ordered by priority) ---\n"
                    + "\n".join(f"- {line}" for line in failure_lines)
                )
            if other:
                other_lines = [f"- {f.check_name}: {f.details}" for f in other[:3]]
                parts.append(
                    "\n\n--- OTHER QA ISSUES (fix if possible without breaking your changes) ---\n"
                    + "\n".join(other_lines)
                )
            scope_constraint = SCOPE_PROMPTS.get("scaffolder", "")
            if scope_constraint:
                parts.append(f"\n\n--- MODIFICATION SCOPE ---\n{scope_constraint}")
        elif context.qa_failures:
            parts.append(
                "\n\n--- QA FAILURES (fix these) ---\n"
                + "\n".join(f"- {f}" for f in context.qa_failures)
            )

        progress = context.metadata.get("progress_anchor", "")
        if progress:
            parts.append(f"\n\n{progress}")

        component_ctx = context.metadata.get("component_context", "")
        if component_ctx:
            parts.append(f"\n\n{component_ctx}")
        audience_ctx = context.metadata.get("audience_context", "")
        if audience_ctx:
            parts.append(f"\n\n{audience_ctx}")
        graph_ctx = context.metadata.get("graph_context", "")
        if graph_ctx:
            parts.append(f"\n\n{graph_ctx}")

        if context.html:
            parts.append("\n\n--- PREVIOUS ATTEMPT (improve this) ---\n" + context.html[:8000])

        return "\n".join(parts)
