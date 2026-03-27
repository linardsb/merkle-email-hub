"""Recovery Router deterministic node — routes QA failures to appropriate fixer nodes."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ai.blueprints.audience_context import AudienceProfile

from app.ai.blueprints.protocols import (
    AgentHandoff,
    AllowedScope,
    NodeContext,
    NodeResult,
    NodeType,
    StructuredFailure,
)
from app.ai.blueprints.route_advisor import is_node_relevant
from app.core.logging import get_logger

logger = get_logger(__name__)

# Priority order: lower number = fix first (most impactful failures)
CHECK_PRIORITY: dict[str, int] = {
    "fallback": 1,
    "accessibility": 2,
    "dark_mode": 3,
    "personalisation_syntax": 4,
    "spam_score": 5,
    "css_support": 6,
    "brand_compliance": 7,
    "link_validation": 8,
    "image_optimization": 9,
    "file_size": 10,
    "html_validation": 11,
}

# Maps check names to suggested fixer agent
CHECK_TO_AGENT: dict[str, str] = {
    "dark_mode": "dark_mode",
    "fallback": "outlook_fixer",
    "accessibility": "accessibility",
    "personalisation_syntax": "personalisation",
    "html_validation": "scaffolder",
    "css_support": "code_reviewer",
    "file_size": "code_reviewer",
    "link_validation": "scaffolder",
    "spam_score": "scaffolder",
    "image_optimization": "scaffolder",
    "brand_compliance": "scaffolder",
}

# Per-agent allowed modification scope on retry
AGENT_SCOPES: dict[str, AllowedScope] = {
    "dark_mode": AllowedScope(styles_only=True),
    "outlook_fixer": AllowedScope(additive_only=True),
    "accessibility": AllowedScope(),
    "personalisation": AllowedScope(text_only=True),
    "code_reviewer": AllowedScope(styles_only=True),
    "scaffolder": AllowedScope(structure_only=True),
}

# Scope constraint prompts for fixer nodes on retry
SCOPE_PROMPTS: dict[str, str] = {
    "scaffolder": "You may modify HTML structure only. Do NOT add new CSS frameworks or external stylesheets.",
    "dark_mode": "You may ONLY modify <style> blocks and inline style attributes. Do NOT change HTML structure or text content.",
    "outlook_fixer": "You may ONLY ADD MSO conditional comments and VML elements. Do NOT remove any existing HTML elements.",
    "accessibility": "You may modify attributes (alt, aria-*, role, lang), text content, and add semantic elements.",
    "code_reviewer": "You may ONLY modify <style> blocks, inline styles, and remove redundant code. Do NOT change text content.",
    "personalisation": "You may ONLY modify text content, template tags, and text-related attributes (alt, title, aria-label).",
}

# Priority order for fixer fallback when audience filters out the primary target.
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


def _fingerprint(sf: StructuredFailure) -> str:
    """Build a compact fingerprint for cycle detection."""
    return f"{sf.check_name}:{hashlib.md5(sf.details.encode()).hexdigest()[:8]}"  # noqa: S324


class RecoveryRouterNode:
    """Deterministic node that examines QA failures and routes to the appropriate fixer.

    Supports two modes:
    1. Structured routing via StructuredFailure objects (priority-based, fingerprint cycle detection)
    2. Legacy string-based routing (backward compatible fallback)
    """

    @property
    def name(self) -> str:
        return "recovery_router"

    @property
    def node_type(self) -> NodeType:
        return "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Analyze failures and decide which fixer node to route to."""
        structured: list[StructuredFailure] = context.metadata.get(  # type: ignore[assignment]
            "qa_failure_details", []
        )

        if not structured and not context.qa_failures:
            logger.warning("blueprint.recovery_router.no_failures")
            return NodeResult(
                status="success",
                html=context.html,
                details="route_to:scaffolder",
            )

        # Fall back to string-based routing if no structured data
        if not structured:
            return self._legacy_route(context)

        # Adaptive fixer selection via outcome ledger (if available)
        recovery_outcome_repo = context.metadata.get("recovery_outcome_repo")
        if recovery_outcome_repo is not None:
            from app.ai.recovery_outcomes import select_best_fixer

            target = await select_best_fixer(
                check_name=structured[0].check_name,
                default_agent=structured[0].suggested_agent,
                project_id=context.metadata.get("project_id"),
                repo=recovery_outcome_repo,
            )
        else:
            # Already sorted by priority from QA gate
            target = structured[0].suggested_agent

        # --- Enhanced cycle detection ---
        history = context.metadata.get("handoff_history", [])
        agents_already_run: set[str] = set()
        for h in history:  # type: ignore[attr-defined]
            if isinstance(h, AgentHandoff):
                agents_already_run.add(h.agent_name)

        # Build fingerprints from previous iteration's failures
        prev_structured: list[StructuredFailure] = context.metadata.get(  # type: ignore[assignment]
            "previous_qa_failure_details", []
        )
        previous_fingerprints: set[str] = {_fingerprint(pf) for pf in prev_structured}

        # Current failure fingerprints
        current_fingerprints: set[str] = {_fingerprint(sf) for sf in structured}

        # If same failures persist after a fixer ran → escalate to scaffolder
        repeated = current_fingerprints & previous_fingerprints
        if target in agents_already_run and repeated:
            logger.warning(
                "blueprint.recovery_router.cycle_detected",
                original_target=target,
                repeated_failures=len(repeated),
                agents_already_run=sorted(agents_already_run),
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
            # Try other agents by priority
            fallback_found = False
            for sf in structured[1:]:
                candidate = sf.suggested_agent
                if candidate != target and is_node_relevant(candidate, audience_profile):
                    target = candidate
                    fallback_found = True
                    break
            if not fallback_found:
                target = "scaffolder"

        # Inject multimodal context for visual defect routing
        self._inject_visual_context(context, structured, target)

        logger.info(
            "blueprint.recovery_router.routing",
            target=target,
            failure_count=len(structured),
            highest_priority_check=structured[0].check_name,
            agents_already_run=sorted(agents_already_run),
        )

        return NodeResult(
            status="success",
            html=context.html,
            details=f"route_to:{target}",
        )

    @staticmethod
    def _inject_visual_context(
        context: NodeContext,
        structured: list[StructuredFailure],
        target: str,
    ) -> None:
        """Inject screenshot into multimodal context when routing visual defects.

        When a visual_defect:* failure routes to a fixer agent, attach the
        screenshot so the fixer can *see* the defect it's fixing.
        """
        import base64

        visual_failures = [sf for sf in structured if sf.check_name.startswith("visual_defect:")]
        if not visual_failures:
            return

        metadata = context.metadata or {}
        raw_screenshots = metadata.get("precheck_screenshots", {})
        if not isinstance(raw_screenshots, dict) or not raw_screenshots:
            return
        screenshots: dict[str, str] = {str(k): str(v) for k, v in raw_screenshots.items()}
        # Find the first screenshot matching a visual defect for this target
        for vf in visual_failures:
            if vf.suggested_agent != target:
                continue
            client_id = vf.check_name.split(":", 1)[1] if ":" in vf.check_name else ""
            b64_data = screenshots.get(client_id)
            if not b64_data:
                continue

            try:
                from app.ai.multimodal import ImageBlock, TextBlock

                image_bytes = base64.b64decode(b64_data)
                override: list[object] = [
                    TextBlock(text=f"Visual defect in {client_id}: {vf.details}"),
                    ImageBlock(data=image_bytes, media_type="image/png", source="base64"),
                ]
                metadata["multimodal_context_override"] = override
                logger.info(
                    "blueprint.recovery_router.visual_context_injected",
                    client=client_id,
                    target=target,
                )
            except Exception:
                logger.warning(
                    "blueprint.recovery_router.visual_context_failed",
                    exc_info=True,
                )
            return  # Inject only one screenshot per routing decision

    def _legacy_route(self, context: NodeContext) -> NodeResult:
        """String-based routing for backward compatibility."""
        has_dark_mode_failure = any(f.startswith("dark_mode:") for f in context.qa_failures)
        has_outlook_failure = any(
            f.startswith("fallback:") or "mso" in f.lower() or "outlook" in f.lower()
            for f in context.qa_failures
        )
        has_accessibility_failure = any(f.startswith("accessibility:") for f in context.qa_failures)
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

        # Also check upstream handoff warnings
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

        # Track agents already run
        history = context.metadata.get("handoff_history", [])
        agents_already_run: set[str] = set()
        for h in history:  # type: ignore[attr-defined]
            if isinstance(h, AgentHandoff):
                agents_already_run.add(h.agent_name)

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
                target = "scaffolder"

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
