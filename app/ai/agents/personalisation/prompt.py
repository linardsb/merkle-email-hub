"""System prompt for the Personalisation agent.

Thin prompt -- core rules only. Detailed patterns loaded from SKILL.md
and skills/*.md via progressive disclosure in the service layer.
"""

from pathlib import Path

from app.ai.agents.evals.failure_warnings import get_failure_warnings
from app.ai.agents.personalisation.schemas import ESPPlatform

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


# L3 reference files -- loaded on demand by detect_relevant_skills()
SKILL_FILES: dict[str, str] = {
    "braze_liquid": "braze_liquid.md",
    "sfmc_ampscript": "sfmc_ampscript.md",
    "adobe_campaign_js": "adobe_campaign_js.md",
    "fallback_patterns": "fallback_patterns.md",
}

PERSONALISATION_SYSTEM_PROMPT = f"""\
You are an expert email personalisation engineer. Your sole task is to
inject ESP-specific dynamic content syntax into email HTML.

{_SKILL_CONTENT}
"""


def build_system_prompt(relevant_skills: list[str]) -> str:
    """Build system prompt with progressive disclosure of L3 reference files.

    Args:
        relevant_skills: List of skill keys to load.

    Returns:
        Complete system prompt with relevant L3 files appended.
    """
    parts = [PERSONALISATION_SYSTEM_PROMPT]

    # Inject eval-informed failure warnings (task 7.2)
    failure_warnings = get_failure_warnings("personalisation")
    if failure_warnings:
        parts.append(f"\n\n{failure_warnings}")

    for skill_key in relevant_skills:
        filename = SKILL_FILES.get(skill_key)
        if filename:
            content = _load_skill_file(filename)
            if content:
                parts.append(f"\n\n--- REFERENCE: {skill_key} ---\n\n{content}")

    return "\n".join(parts)


def detect_relevant_skills(platform: ESPPlatform, requirements: str) -> list[str]:
    """Detect which L3 skill files are relevant based on platform and requirements.

    Progressive disclosure -- load the platform-specific file + fallback patterns.

    Args:
        platform: Target ESP platform.
        requirements: Natural language personalisation requirements.

    Returns:
        List of relevant skill keys.
    """
    skills: list[str] = []

    # Always load fallback patterns
    skills.append("fallback_patterns")

    # Load platform-specific skill
    platform_map: dict[ESPPlatform, str] = {
        "braze": "braze_liquid",
        "sfmc": "sfmc_ampscript",
        "adobe_campaign": "adobe_campaign_js",
    }
    platform_skill = platform_map.get(platform)
    if platform_skill:
        skills.append(platform_skill)

    # Cross-platform references only if requirements mention another platform
    req_lower = requirements.lower()
    if platform != "braze" and ("liquid" in req_lower or "braze" in req_lower):
        skills.append("braze_liquid")
    if platform != "sfmc" and ("ampscript" in req_lower or "sfmc" in req_lower):
        skills.append("sfmc_ampscript")
    if platform != "adobe_campaign" and ("adobe" in req_lower or "jssp" in req_lower):
        skills.append("adobe_campaign_js")

    return list(dict.fromkeys(skills))  # deduplicate preserving order
