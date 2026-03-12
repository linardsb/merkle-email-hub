"""Recovery Router deterministic node — routes QA failures to appropriate fixer nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ai.blueprints.audience_context import AudienceProfile

from app.ai.blueprints.protocols import AgentHandoff, NodeContext, NodeResult, NodeType
from app.ai.blueprints.route_advisor import is_node_relevant
from app.core.logging import get_logger

logger = get_logger(__name__)

# Maps QA check names to the node that can fix them.
# Dark mode failures → dark_mode node; fallback/MSO → outlook_fixer; rest → scaffolder.
_FAILURE_ROUTING: dict[str, str] = {
    "dark_mode": "dark_mode",
    "fallback": "outlook_fixer",
    "accessibility": "accessibility",
    "html_validation": "scaffolder",
    "css_support": "code_reviewer",
    "file_size": "code_reviewer",
    "link_validation": "scaffolder",
    "spam_score": "scaffolder",
    "image_optimization": "scaffolder",
    "brand_compliance": "scaffolder",
}


# Priority order for fixer fallback when audience filters out the primary target.
# Scaffolder is last — always relevant, always available as a general fixer.
_FIXER_PRIORITY = (
    "dark_mode",
    "outlook_fixer",
    "accessibility",
    "personalisation",
    "code_reviewer",
    "scaffolder",
)


def _has_matching_failure(
    candidate: str,
    qa_failures: list[str],
    upstream: AgentHandoff | object | None,
) -> bool:
    """Check if the candidate fixer has a matching failure in QA results or upstream warnings."""
    _CANDIDATE_PATTERNS: dict[str, tuple[str, ...]] = {
        "dark_mode": ("dark_mode:",),
        "outlook_fixer": ("fallback:", "mso", "outlook"),
        "accessibility": ("accessibility:",),
        "personalisation": ("personalisation", "personalization", "liquid", "ampscript"),
        "code_reviewer": ("code_review", "redundant", "css_support", "file_size"),
    }
    patterns = _CANDIDATE_PATTERNS.get(candidate, ())
    if not patterns:
        return False

    for f in qa_failures:
        if any(p in f.lower() for p in patterns):
            return True

    if isinstance(upstream, AgentHandoff):
        for w in upstream.warnings:
            if any(p in w.lower() for p in patterns):
                return True

    return False


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

        # Determine if any failures are accessibility-specific
        has_accessibility_failure = any(f.startswith("accessibility:") for f in context.qa_failures)

        # Determine if any failures are code-review-specific
        has_code_review_failure = any(
            any(
                kw in f.lower()
                for kw in (
                    "code_review",
                    "redundant",
                    "css_support",
                    "nesting",
                    "file_size",
                    "unsupported css",
                )
            )
            for f in context.qa_failures
        )

        # Determine if any failures are personalisation-specific
        # NOTE: "fallback" was removed — it collides with MSO fallback check names
        # (e.g. "fallback: No MSO conditional comments") causing misrouting.
        has_personalisation_failure = any(
            any(
                kw in f.lower()
                for kw in (
                    "personalisation",
                    "personalization",
                    "liquid",
                    "ampscript",
                    "dynamic content",
                    "merge tag",
                )
            )
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
            if not has_accessibility_failure:
                has_accessibility_failure = any(
                    kw in w.lower()
                    for w in upstream.warnings
                    for kw in ("accessibility", "wcag", "alt text", "contrast")
                )
            if not has_code_review_failure:
                has_code_review_failure = any(
                    any(
                        kw in w.lower()
                        for kw in ("code_review", "redundant", "unsupported css", "file_size")
                    )
                    for w in upstream.warnings
                )
            if not has_personalisation_failure:
                has_personalisation_failure = any(
                    any(
                        kw in w.lower()
                        for kw in (
                            "personalisation",
                            "personalization",
                            "liquid",
                            "ampscript",
                            "dynamic content",
                            "merge tag",
                        )
                    )
                    for w in upstream.warnings
                )

        # Track which agents already ran via handoff_history to avoid cycles
        history = context.metadata.get("handoff_history", [])
        agents_already_run: set[str] = set()
        all_history_warnings: list[str] = []
        for h in history:  # type: ignore[attr-defined]
            if isinstance(h, AgentHandoff):
                agents_already_run.add(h.agent_name)
                all_history_warnings.extend(h.warnings)

        if has_dark_mode_failure:
            target = "dark_mode"
        elif has_outlook_failure:
            target = "outlook_fixer"
        elif has_accessibility_failure:
            target = "accessibility"
        elif has_personalisation_failure:
            target = "personalisation"
        elif has_code_review_failure:
            target = "code_reviewer"
        else:
            target = "scaffolder"

        # If the target agent already ran and the same failure persists,
        # fall back to scaffolder (general fixer) to avoid infinite loops
        if target in agents_already_run and context.iteration > 0:
            logger.warning(
                "blueprint.recovery_router.cycle_detected",
                original_target=target,
                agents_already_run=sorted(agents_already_run),
                iteration=context.iteration,
            )
            target = "scaffolder"

        # Filter out audience-irrelevant fixers
        raw_profile = context.metadata.get("audience_profile")
        audience_profile: AudienceProfile | None = raw_profile if raw_profile is not None else None  # type: ignore[assignment]
        if not is_node_relevant(target, audience_profile):
            logger.info(
                "blueprint.recovery_router.audience_filtered",
                original_target=target,
                reason="audience_irrelevant",
            )
            fallback_found = False
            for candidate in _FIXER_PRIORITY:
                if candidate == target:
                    continue
                if _has_matching_failure(
                    candidate, context.qa_failures, upstream
                ) and is_node_relevant(candidate, audience_profile):
                    target = candidate
                    fallback_found = True
                    break
            if not fallback_found:
                target = "scaffolder"  # Always relevant, always available

        logger.info(
            "blueprint.recovery_router.routing",
            target=target,
            failure_count=len(context.qa_failures),
            agents_already_run=sorted(agents_already_run),
        )

        return NodeResult(
            status="success",
            html=context.html,
            details=f"route_to:{target}",
        )
