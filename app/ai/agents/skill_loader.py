"""Shared utility for output-mode-aware SKILL.md section extraction.

Phase 5 addition: Budget-aware skill loading with front matter metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

OutputMode = Literal["html", "structured"]

_OUTPUT_FORMAT_RE = re.compile(r"^## Output Format: (.+)$", re.MULTILINE)
_SECURITY_RULES_RE = re.compile(r"^## Security Rules.*$", re.MULTILINE)
_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class SkillMeta:
    """Metadata parsed from skill file front matter.

    Attributes:
        token_cost: Estimated token cost of loading this skill file.
        priority: Loading priority (1=critical, 2=standard, 3=supplementary).
    """

    token_cost: int = 500
    priority: int = 2


def parse_skill_meta(content: str) -> tuple[SkillMeta, str]:
    """Parse YAML-like front matter from a skill file.

    Returns (metadata, remaining_content). If no front matter is found,
    returns default SkillMeta and original content (backward compatible).
    """
    match = _FRONT_MATTER_RE.match(content)
    if not match:
        return SkillMeta(), content

    front_matter = match.group(1)
    body = content[match.end() :]

    token_cost = 500
    priority = 2

    for line in front_matter.strip().splitlines():
        line = line.strip()
        if line.startswith("token_cost:"):
            try:
                token_cost = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("priority:"):
            try:
                priority = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass

    return SkillMeta(token_cost=token_cost, priority=priority), body


def should_load_skill(
    meta: SkillMeta,
    cumulative_cost: int,
    remaining_budget: int,
    budget_max: int,
) -> bool:
    """Decide whether to load a skill file based on budget constraints.

    Priority 1 (critical): always loaded.
    Priority 2 (standard): skipped when budget is below 30% capacity.
    Priority 3 (supplementary): skipped when any budget pressure exists (below 70%).

    Args:
        meta: Skill file metadata.
        cumulative_cost: Tokens already consumed by previously loaded skills.
        remaining_budget: Remaining token budget for skill docs.
        budget_max: Total skill docs budget from ContextBudget.

    Returns:
        True if the skill should be loaded.
    """
    if meta.priority == 1:
        return True

    available = remaining_budget - cumulative_cost
    if available < meta.token_cost:
        return False

    capacity_ratio = available / budget_max if budget_max > 0 else 0.0

    if meta.priority == 3 and capacity_ratio < 0.70:
        return False

    if meta.priority == 2 and capacity_ratio < 0.30:
        return False

    return True


def extract_skill_for_mode(skill_content: str, output_mode: str = "html") -> str:
    """Extract shared sections + the matching output format section from SKILL.md.

    Returns the full SKILL.md content with only the relevant output format
    section included. If no output format sections are found (legacy SKILL.md),
    returns the content unchanged for backward compatibility.

    Args:
        skill_content: Full SKILL.md content (L1 frontmatter + L2 body).
        output_mode: "html" or "structured".

    Returns:
        SKILL.md content with only the matching output format section.
    """
    format_matches = list(_OUTPUT_FORMAT_RE.finditer(skill_content))
    if not format_matches:
        return skill_content  # No output format sections -- backward compatible

    # Everything before first Output Format header = shared domain knowledge
    shared_end = format_matches[0].start()
    shared = skill_content[:shared_end].rstrip()

    # Find the matching output format section
    target = "HTML" if output_mode == "html" else "Structured"
    mode_section = ""
    for i, match in enumerate(format_matches):
        if match.group(1).strip().startswith(target):
            start = match.start()
            # Section extends to next Output Format header, Security Rules, or EOF
            end = len(skill_content)
            if i + 1 < len(format_matches):
                end = format_matches[i + 1].start()
            else:
                # Check for Security Rules after last format section
                sec_match = _SECURITY_RULES_RE.search(skill_content, start + 1)
                if sec_match:
                    end = sec_match.start()
            mode_section = skill_content[start:end].rstrip()
            break

    # Security Rules section (after all Output Format sections) -- always included
    security = ""
    sec_match = _SECURITY_RULES_RE.search(skill_content, format_matches[-1].start())
    if sec_match:
        security = skill_content[sec_match.start() :].rstrip()

    parts = [shared]
    if mode_section:
        parts.append(mode_section)
    if security:
        parts.append(security)

    return "\n\n".join(parts)
