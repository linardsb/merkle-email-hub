"""System prompt for the Code Reviewer agent.

Thin prompt -- core rules only. Detailed patterns loaded from SKILL.md
and skills/*.md via progressive disclosure in the service layer.
"""

from pathlib import Path

from app.ai.agents.code_reviewer.schemas import ReviewFocus
from app.ai.agents.evals.failure_warnings import get_failure_warnings
from app.ai.agents.skill_override import get_override

_SKILL_DIR = Path(__file__).parent

# Load L1+L2 instructions from SKILL.md (always loaded)
_SKILL_PATH = _SKILL_DIR / "SKILL.md"
_SKILL_CONTENT = _SKILL_PATH.read_text(encoding="utf-8") if _SKILL_PATH.exists() else ""

_PROMPT_PREFIX = """\
You are an expert email HTML code reviewer. Your sole task is to
analyse email HTML and report issues — you NEVER modify the source HTML.
"""


def _load_skill_file(name: str) -> str:
    """Load an L3 skill reference file by name."""
    path = _SKILL_DIR / "skills" / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


# L3 reference files -- loaded on demand by detect_relevant_skills()
SKILL_FILES: dict[str, str] = {
    "redundant_code": "redundant_code.md",
    "css_client_support": "css_client_support.md",
    "nesting_validation": "nesting_validation.md",
    "file_size_optimization": "file_size_optimization.md",
}


def _base_system_prompt() -> str:
    """Build base system prompt, checking for A/B test override."""
    skill = get_override("code_reviewer") or _SKILL_CONTENT
    return f"{_PROMPT_PREFIX}\n{skill}"


def build_system_prompt(relevant_skills: list[str]) -> str:
    """Build system prompt with progressive disclosure of L3 reference files.

    Args:
        relevant_skills: List of skill keys to load.

    Returns:
        Complete system prompt with relevant L3 files appended.
    """
    parts = [_base_system_prompt()]

    # Inject eval-informed failure warnings (task 7.2)
    failure_warnings = get_failure_warnings("code_reviewer")
    if failure_warnings:
        parts.append(f"\n\n{failure_warnings}")

    for skill_key in relevant_skills:
        filename = SKILL_FILES.get(skill_key)
        if filename:
            content = _load_skill_file(filename)
            if content:
                parts.append(f"\n\n--- REFERENCE: {skill_key} ---\n\n{content}")

    return "\n".join(parts)


def detect_relevant_skills(focus: ReviewFocus) -> list[str]:
    """Detect which L3 skill files are relevant based on review focus.

    Args:
        focus: Review focus area.

    Returns:
        List of relevant skill keys.
    """
    if focus == "all":
        return list(SKILL_FILES.keys())

    focus_map: dict[ReviewFocus, list[str]] = {
        "redundant_code": ["redundant_code"],
        "css_support": ["css_client_support"],
        "nesting": ["nesting_validation"],
        "file_size": ["file_size_optimization"],
    }
    return focus_map.get(focus, list(SKILL_FILES.keys()))
