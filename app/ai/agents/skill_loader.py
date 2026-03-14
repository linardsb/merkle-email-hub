"""Shared utility for output-mode-aware SKILL.md section extraction."""

from __future__ import annotations

import re
from typing import Literal

OutputMode = Literal["html", "structured"]

_OUTPUT_FORMAT_RE = re.compile(r"^## Output Format: (.+)$", re.MULTILINE)
_SECURITY_RULES_RE = re.compile(r"^## Security Rules.*$", re.MULTILINE)


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
