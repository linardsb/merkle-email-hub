"""System prompt for the Content agent.

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
    "spam_triggers": "spam_triggers.md",
    "subject_line_formulas": "subject_line_formulas.md",
    "brand_voice": "brand_voice.md",
    "operation_best_practices": "operation_best_practices.md",
}

CONTENT_SYSTEM_PROMPT = f"""\
You are an expert email marketing copywriter specialising in high-conversion email copy.
Your task: generate or refine email marketing text based on the requested operation.

{_SKILL_CONTENT}
"""


def build_system_prompt(relevant_skills: list[str]) -> str:
    """Build system prompt with progressive disclosure of L3 reference files.

    Args:
        relevant_skills: List of skill keys to load (e.g., ['spam_triggers', 'brand_voice']).

    Returns:
        Complete system prompt with relevant L3 files appended.
    """
    parts = [CONTENT_SYSTEM_PROMPT]

    for skill_key in relevant_skills:
        filename = SKILL_FILES.get(skill_key)
        if filename:
            content = _load_skill_file(filename)
            if content:
                parts.append(f"\n\n--- REFERENCE: {skill_key} ---\n\n{content}")

    return "\n".join(parts)


def detect_relevant_skills(
    operation: str,
    brand_voice: str | None = None,
    text: str | None = None,
) -> list[str]:
    """Detect which L3 skill files are relevant based on the operation and context.

    Progressive disclosure — only load skill files for detected needs.

    Args:
        operation: Content operation type (subject_line, preheader, cta, etc.).
        brand_voice: Optional brand voice guidelines.
        text: Optional source text to analyze.

    Returns:
        List of relevant skill keys.
    """
    skills: list[str] = []

    # Always load operation best practices
    skills.append("operation_best_practices")

    # Subject line operations need formula reference
    if operation in ("subject_line", "preheader"):
        skills.append("subject_line_formulas")

    # Brand voice provided — load brand voice reference
    if brand_voice:
        skills.append("brand_voice")

    # Tone adjustment needs brand voice framework
    if operation == "tone_adjust":
        skills.append("brand_voice")

    # Always load spam triggers for any content generation
    skills.append("spam_triggers")

    return list(dict.fromkeys(skills))  # deduplicate preserving order
