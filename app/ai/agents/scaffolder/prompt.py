"""System prompt for the Scaffolder agent.

Thin prompt — core rules only. Detailed patterns loaded from SKILL.md
and skills/*.md via progressive disclosure in the service layer.
"""

from pathlib import Path

from app.ai.agents.evals.failure_warnings import get_failure_warnings
from app.ai.agents.skill_loader import extract_skill_for_mode
from app.ai.agents.skill_override import get_override

_SKILL_DIR = Path(__file__).parent

# Load L1+L2 instructions from SKILL.md (always loaded)
_SKILL_PATH = _SKILL_DIR / "SKILL.md"
_SKILL_CONTENT = _SKILL_PATH.read_text(encoding="utf-8") if _SKILL_PATH.exists() else ""

_PROMPT_PREFIX = """\
You are an expert email developer specialising in Maizzle (Tailwind CSS for email).
Your task: generate a complete, production-ready Maizzle email template from a campaign brief.
"""


def _load_skill_file(name: str) -> str:
    """Load an L3 skill reference file by name."""
    path = _SKILL_DIR / "skills" / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


# L3 reference files — loaded on demand by detect_relevant_skills()
SKILL_FILES: dict[str, str] = {
    "table_layouts": "table_layouts.md",
    "maizzle_syntax": "maizzle_syntax.md",
    "client_compatibility": "client_compatibility.md",
    "mso_vml_quick_ref": "mso_vml_quick_ref.md",
    "email_structure": "email_structure.md",
    "css_email_reference": "css_email_reference.md",
}


def _base_system_prompt(output_mode: str = "html") -> str:
    """Build base system prompt with output-mode-aware section extraction."""
    skill = get_override("scaffolder") or _SKILL_CONTENT
    skill = extract_skill_for_mode(skill, output_mode)
    return f"{_PROMPT_PREFIX}\n{skill}"


def build_system_prompt(relevant_skills: list[str], output_mode: str = "html") -> str:
    """Build system prompt with progressive disclosure of L3 reference files.

    Args:
        relevant_skills: List of skill keys to load (e.g., ['table_layouts', 'maizzle_syntax']).
        output_mode: "html" or "structured" — controls which output format section is included.

    Returns:
        Complete system prompt with relevant L3 files appended.
    """
    parts = [_base_system_prompt(output_mode)]

    # Inject eval-informed failure warnings (task 7.2)
    failure_warnings = get_failure_warnings("scaffolder")
    if failure_warnings:
        parts.append(f"\n\n{failure_warnings}")

    for skill_key in relevant_skills:
        filename = SKILL_FILES.get(skill_key)
        if filename:
            content = _load_skill_file(filename)
            if content:
                parts.append(f"\n\n--- REFERENCE: {skill_key} ---\n\n{content}")

    return "\n".join(parts)


def detect_relevant_skills(brief: str, context: dict[str, str] | None = None) -> list[str]:
    """Detect which L3 skill files are relevant based on the campaign brief.

    Progressive disclosure — only load skill files for detected needs.

    Args:
        brief: Campaign brief text to analyze.
        context: Optional additional context hints.

    Returns:
        List of relevant skill keys.
    """
    brief_lower = brief.lower()
    skills: list[str] = []

    # Always load Maizzle syntax reference
    skills.append("maizzle_syntax")

    # MSO-first: ALWAYS load MSO/VML reference — every email needs Outlook support
    skills.append("mso_vml_quick_ref")

    # Multi-column layouts need table layout reference
    if any(
        kw in brief_lower
        for kw in [
            "column",
            "grid",
            "sidebar",
            "side-by-side",
            "two-col",
            "three-col",
            "2-col",
            "3-col",
            "multi-column",
            "split",
            "cards",
        ]
    ):
        skills.append("table_layouts")

    # Email structure (preheader, header, footer, hero, accessibility, images)
    if any(
        kw in brief_lower
        for kw in [
            "preheader",
            "preview text",
            "header",
            "footer",
            "hero",
            "banner",
            "unsubscribe",
            "accessibility",
            "a11y",
            "alt text",
            "logo",
        ]
    ):
        skills.append("email_structure")

    # Client compatibility concerns
    if any(
        kw in brief_lower
        for kw in [
            "gmail",
            "yahoo",
            "apple mail",
            "client",
            "compatibility",
            "clipping",
            "102kb",
            "dark mode",
            "responsive",
        ]
    ):
        skills.append("client_compatibility")

    # Complex briefs — load everything
    if len(brief) > 2000 or (context and context.get("complexity") == "high"):
        skills = list(SKILL_FILES.keys())

    return list(dict.fromkeys(skills))  # deduplicate preserving order
