"""System prompt for the Outlook Fixer agent.

Thin prompt — core rules only. Detailed patterns loaded from SKILL.md
and skills/*.md via progressive disclosure in the service layer.
"""

from pathlib import Path

_SKILL_DIR = Path(__file__).parent

# Load L1+L2 instructions from SKILL.md (always loaded)
_SKILL_PATH = _SKILL_DIR / "SKILL.md"
_SKILL_CONTENT = _SKILL_PATH.read_text(encoding="utf-8") if _SKILL_PATH.exists() else ""


def _load_skill_file(name: str) -> str:
    """Load an L3 skill reference file by name."""
    path = _SKILL_DIR / "skills" / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


# L3 reference files — loaded on demand by detect_relevant_skills()
SKILL_FILES: dict[str, str] = {
    "mso_bug_fixes": "mso_bug_fixes.md",
    "vml_reference": "vml_reference.md",
    "mso_conditionals": "mso_conditionals.md",
    "diagnostic": "diagnostic.md",
}

OUTLOOK_FIXER_SYSTEM_PROMPT = f"""\
You are an expert Outlook email compatibility engineer. Your sole task is to
fix Outlook desktop rendering issues in email HTML.

{_SKILL_CONTENT}
"""


def build_system_prompt(relevant_skills: list[str]) -> str:
    """Build system prompt with progressive disclosure of L3 reference files.

    Args:
        relevant_skills: List of skill keys to load (e.g., ['vml_reference', 'mso_conditionals']).

    Returns:
        Complete system prompt with relevant L3 files appended.
    """
    parts = [OUTLOOK_FIXER_SYSTEM_PROMPT]

    for skill_key in relevant_skills:
        filename = SKILL_FILES.get(skill_key)
        if filename:
            content = _load_skill_file(filename)
            if content:
                parts.append(f"\n\n--- REFERENCE: {skill_key} ---\n\n{content}")

    return "\n".join(parts)


def detect_relevant_skills(html: str, issues: list[str] | None = None) -> list[str]:
    """Detect which L3 skill files are relevant based on input HTML patterns.

    Progressive disclosure — only load skill files for detected issue types.

    Args:
        html: Input email HTML to analyze.
        issues: Optional explicit list of issue types.

    Returns:
        List of relevant skill keys.
    """
    html_lower = html.lower()
    skills: list[str] = []

    # Always load diagnostic for symptom lookup
    skills.append("diagnostic")

    if issues:
        # Explicit issue list — load matching skills
        issue_set = {i.lower() for i in issues}
        if issue_set & {"vml", "vml_reference", "background_image", "bulletproof_button"}:
            skills.append("vml_reference")
        if issue_set & {"mso", "mso_conditionals", "ghost_table", "ghost_tables", "dpi"}:
            skills.append("mso_conditionals")
        if issue_set & {"bug_fixes", "mso_bug_fixes", "font", "line_height", "spacing", "image"}:
            skills.append("mso_bug_fixes")
    else:
        # Auto-detect from HTML content
        if "<v:" in html_lower or "vml" in html_lower or "v:roundrect" in html_lower:
            skills.append("vml_reference")

        if "<!--[if" in html or "mso" in html_lower or "ghost" in html_lower:
            skills.append("mso_conditionals")

        # Always load bug fixes — the agent needs these for comprehensive fixing
        skills.append("mso_bug_fixes")

    return list(dict.fromkeys(skills))  # deduplicate preserving order
