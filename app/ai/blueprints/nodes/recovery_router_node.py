"""Recovery Router deterministic node — routes QA failures to appropriate fixer nodes."""

from app.ai.blueprints.protocols import AgentHandoff, NodeContext, NodeResult, NodeType
from app.core.logging import get_logger

logger = get_logger(__name__)

# Maps QA check names to the node that can fix them.
# Dark mode failures → dark_mode node; fallback/MSO → outlook_fixer; rest → scaffolder.
_FAILURE_ROUTING: dict[str, str] = {
    "dark_mode": "dark_mode",
    "fallback": "outlook_fixer",
    "accessibility": "scaffolder",
    "html_validation": "scaffolder",
    "css_support": "scaffolder",
    "file_size": "scaffolder",
    "link_validation": "scaffolder",
    "spam_score": "scaffolder",
    "image_optimization": "scaffolder",
    "brand_compliance": "scaffolder",
}


class RecoveryRouterNode:
    """Deterministic node that examines QA failures and routes to the appropriate fixer.

    Parses failure details to identify which check failed, then routes to the
    relevant fixer node via metadata in the result details.
    """

    @property
    def name(self) -> str:
        return "recovery_router"

    @property
    def node_type(self) -> NodeType:
        return "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Analyze failures and decide which fixer node to route to."""
        if not context.qa_failures:
            logger.warning("blueprint.recovery_router.no_failures")
            return NodeResult(
                status="success",
                html=context.html,
                details="route_to:scaffolder",
            )

        # Determine if any failures are dark-mode-specific
        has_dark_mode_failure = any(f.startswith("dark_mode:") for f in context.qa_failures)

        # Determine if any failures are Outlook/MSO/fallback-specific
        has_outlook_failure = any(
            f.startswith("fallback:") or "mso" in f.lower() or "outlook" in f.lower()
            for f in context.qa_failures
        )

        # Also check upstream handoff warnings for routing hints
        upstream = context.metadata.get("upstream_handoff")
        if isinstance(upstream, AgentHandoff) and upstream.warnings:
            if not has_dark_mode_failure:
                has_dark_mode_failure = any(
                    "dark mode" in w.lower() or "dark_mode" in w.lower() for w in upstream.warnings
                )
            if not has_outlook_failure:
                has_outlook_failure = any(
                    "outlook" in w.lower() or "mso" in w.lower() or "vml" in w.lower()
                    for w in upstream.warnings
                )

        if has_dark_mode_failure:
            target = "dark_mode"
        elif has_outlook_failure:
            target = "outlook_fixer"
        else:
            target = "scaffolder"

        logger.info(
            "blueprint.recovery_router.routing",
            target=target,
            failure_count=len(context.qa_failures),
        )

        return NodeResult(
            status="success",
            html=context.html,
            details=f"route_to:{target}",
        )
