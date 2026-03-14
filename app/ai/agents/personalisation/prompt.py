"""System prompt for the Personalisation agent.

Thin prompt -- core rules only. Detailed patterns loaded from SKILL.md
and skills/*.md via progressive disclosure in the service layer.
"""

from pathlib import Path

from app.ai.agents.evals.failure_warnings import get_failure_warnings
from app.ai.agents.personalisation.schemas import ESPPlatform
from app.ai.agents.skill_loader import extract_skill_for_mode
from app.ai.agents.skill_override import get_override

_SKILL_DIR = Path(__file__).parent

# Load L1+L2 instructions from SKILL.md (always loaded)
_SKILL_PATH = _SKILL_DIR / "SKILL.md"
_SKILL_CONTENT = _SKILL_PATH.read_text(encoding="utf-8") if _SKILL_PATH.exists() else ""

_PROMPT_PREFIX = """\
You are an expert email personalisation engineer. Your sole task is to
inject ESP-specific dynamic content syntax into email HTML.
"""


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
    "klaviyo_django": "klaviyo_django.md",
    "mailchimp_merge": "mailchimp_merge.md",
    "hubspot_hubl": "hubspot_hubl.md",
    "iterable_handlebars": "iterable_handlebars.md",
    "fallback_patterns": "fallback_patterns.md",
}


def _base_system_prompt(output_mode: str = "html") -> str:
    """Build base system prompt with output-mode-aware section extraction."""
    skill = get_override("personalisation") or _SKILL_CONTENT
    skill = extract_skill_for_mode(skill, output_mode)
    return f"{_PROMPT_PREFIX}\n{skill}"


def build_system_prompt(relevant_skills: list[str], output_mode: str = "html") -> str:
    """Build system prompt with progressive disclosure of L3 reference files.

    Args:
        relevant_skills: List of skill keys to load.
        output_mode: "html" or "structured" — controls which output format section is included.

    Returns:
        Complete system prompt with relevant L3 files appended.
    """
    parts = [_base_system_prompt(output_mode)]

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
        "klaviyo": "klaviyo_django",
        "mailchimp": "mailchimp_merge",
        "hubspot": "hubspot_hubl",
        "iterable": "iterable_handlebars",
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
    if platform != "klaviyo" and ("klaviyo" in req_lower or "django template" in req_lower):
        skills.append("klaviyo_django")
    if platform != "mailchimp" and ("mailchimp" in req_lower or "merge tag" in req_lower):
        skills.append("mailchimp_merge")
    if platform != "hubspot" and ("hubspot" in req_lower or "hubl" in req_lower):
        skills.append("hubspot_hubl")
    if platform != "iterable" and ("iterable" in req_lower or "handlebars" in req_lower):
        skills.append("iterable_handlebars")

    return list(dict.fromkeys(skills))  # deduplicate preserving order
