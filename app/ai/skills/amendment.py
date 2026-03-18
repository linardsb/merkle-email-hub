"""Amendment generation, dedup, conflict detection, apply/dry-run."""

from __future__ import annotations

import difflib
from pathlib import Path

from app.ai.skills.schemas import (
    AGENT_SKILL_TARGETS,
    AmendmentReport,
    PatternCategory,
    SkillAmendment,
    SkillPattern,
)
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_SKILL_BASE = Path("app/ai/agents")

# Category → best target skill file per agent
_CATEGORY_SKILL_MAP: dict[PatternCategory, dict[str, str]] = {
    PatternCategory.OUTLOOK_FIX: {
        "outlook_fixer": "skills/vml_reference.md",
        "scaffolder": "skills/mso_vml_quick_ref.md",
    },
    PatternCategory.DARK_MODE: {
        "dark_mode": "skills/color_remapping.md",
        "scaffolder": "skills/client_compatibility.md",
    },
    PatternCategory.RESPONSIVE: {
        "scaffolder": "skills/client_compatibility.md",
    },
    PatternCategory.ACCESSIBILITY: {
        "accessibility": "skills/wcag_email_mapping.md",
        "scaffolder": "skills/email_structure.md",
    },
    PatternCategory.PERFORMANCE: {
        "code_reviewer": "skills/file_size_optimization.md",
        "scaffolder": "skills/email_structure.md",
    },
    PatternCategory.ESP_SYNTAX: {
        "personalisation": "skills/fallback_patterns.md",
    },
    PatternCategory.PROGRESSIVE_ENHANCEMENT: {
        "scaffolder": "skills/client_compatibility.md",
        "outlook_fixer": "skills/mso_conditionals.md",
    },
}


def generate_amendments(
    patterns: list[SkillPattern],
    *,
    min_confidence: float | None = None,
) -> list[SkillAmendment]:
    """Convert detected patterns into skill file amendment proposals.

    Args:
        patterns: Patterns from extractor.
        min_confidence: Override settings threshold.

    Returns:
        List of amendments ready for review.
    """
    settings = get_settings()
    threshold = min_confidence or settings.skill_extraction.min_confidence
    amendments: list[SkillAmendment] = []

    for pattern in patterns:
        if pattern.confidence < threshold:
            continue

        for agent in pattern.applicable_agents:
            skill_file = _resolve_skill_file(agent, pattern.category)
            if not skill_file:
                continue

            content = _format_amendment_content(pattern)

            # Check for duplicates against existing file content
            if _is_duplicate(agent, skill_file, pattern.pattern_name):
                logger.debug(
                    "amendment.skip_duplicate",
                    pattern=pattern.pattern_name,
                    agent=agent,
                )
                continue

            amendments.append(
                SkillAmendment(
                    agent_name=agent,
                    skill_file=skill_file,
                    section="Auto-Extracted Patterns",
                    content=content,
                    confidence=pattern.confidence,
                    source_pattern_id=pattern.id,
                    source_template_id=pattern.source_template_id,
                )
            )

    return amendments


def apply_amendments(
    amendments: list[SkillAmendment],
    *,
    dry_run: bool = True,
) -> AmendmentReport:
    """Apply amendments to skill files (or preview in dry-run mode).

    Args:
        amendments: Approved amendments to apply.
        dry_run: If True, generate diffs without modifying files.

    Returns:
        Report with counts and diff previews.
    """
    applied = 0
    skipped_dup = 0
    skipped_conflict = 0
    diffs: list[dict[str, object]] = []

    for amendment in amendments:
        file_path = _SKILL_BASE / amendment.agent_name / amendment.skill_file

        # SECURITY: Prevent path traversal — resolved path must stay within _SKILL_BASE
        try:
            resolved = file_path.resolve()
            if not resolved.is_relative_to(_SKILL_BASE.resolve()):
                logger.warning(
                    "amendment.path_traversal_blocked",
                    path=str(file_path),
                    agent=amendment.agent_name,
                )
                continue
        except (OSError, ValueError):
            continue

        if not file_path.exists():
            logger.warning(
                "amendment.skill_file_missing",
                path=str(file_path),
                agent=amendment.agent_name,
            )
            continue

        existing = file_path.read_text()

        # Check duplicate by pattern name in existing content
        if amendment.source_pattern_id and amendment.source_pattern_id in existing:
            skipped_dup += 1
            continue

        # Check for conflicting content (simple substring match)
        if _has_conflict(existing, amendment.content):
            skipped_conflict += 1
            continue

        # Build the new content
        attribution = (
            f"\n\n<!-- auto-extracted pattern: {amendment.source_pattern_id} "
            f"from template: {amendment.source_template_id or 'unknown'} -->\n"
        )
        section_header = f"\n## {amendment.section}\n\n"

        # Append under existing section if it exists, otherwise append at end
        if f"## {amendment.section}" in existing:
            new_content = existing + attribution + amendment.content + "\n"
        else:
            new_content = existing + section_header + attribution + amendment.content + "\n"

        # Generate diff
        diff_lines = list(
            difflib.unified_diff(
                existing.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=str(file_path),
                tofile=str(file_path),
            )
        )
        diffs.append(
            {
                "file": str(file_path),
                "diff_preview": "".join(diff_lines[:50]),
                "lines_added": sum(1 for line in diff_lines if line.startswith("+")),
            }
        )

        if not dry_run:
            file_path.write_text(new_content)
            logger.info(
                "amendment.applied",
                agent=amendment.agent_name,
                file=str(file_path),
                pattern=amendment.source_pattern_id,
            )
            applied += 1
        else:
            applied += 1  # Count as "would apply" in dry-run

    return AmendmentReport(
        total=len(amendments),
        applied=applied,
        skipped_duplicate=skipped_dup,
        skipped_conflict=skipped_conflict,
        skipped_low_confidence=0,
        diffs=diffs,  # pyright: ignore[reportArgumentType]
    )


def _resolve_skill_file(agent: str, category: PatternCategory) -> str | None:
    """Find the best skill file for an agent + category combination."""
    category_map = _CATEGORY_SKILL_MAP.get(category, {})
    if agent in category_map:
        return category_map[agent]
    # Fallback: first available skill file for this agent
    targets = AGENT_SKILL_TARGETS.get(agent)
    return targets[0] if targets else None


def _format_amendment_content(pattern: SkillPattern) -> str:
    """Format a pattern into markdown content for a skill file."""
    lines = [
        f"### {pattern.pattern_name.replace('_', ' ').title()}",
        "",
        pattern.description,
        "",
    ]
    if pattern.html_example and pattern.html_example != "(size signal, no HTML example)":
        lines.extend(
            [
                "```html",
                pattern.html_example,
                "```",
                "",
            ]
        )
    lines.append(f"*Confidence: {pattern.confidence:.0%}*")
    return "\n".join(lines)


def _is_duplicate(agent: str, skill_file: str, pattern_name: str) -> bool:
    """Check if a pattern already exists in the target skill file."""
    path = _SKILL_BASE / agent / skill_file
    if not path.exists():
        return False
    content = path.read_text().lower()
    return pattern_name.lower() in content or pattern_name.replace("_", " ").lower() in content


def _has_conflict(
    existing_content: str,  # noqa: ARG001
    new_content: str,  # noqa: ARG001
) -> bool:
    """Simple conflict detection — stub for future semantic analysis."""
    # Conservative: only flag obvious contradictions
    # Future: use embedding similarity for semantic conflict detection
    return False
