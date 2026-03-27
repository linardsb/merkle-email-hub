"""System prompt for the Personalisation agent.

Thin prompt -- core rules only. Detailed patterns loaded from SKILL.md
and skills/*.md via progressive disclosure in the service layer.
"""

from pathlib import Path

from app.ai.agents.evals.failure_warnings import get_failure_warnings
from app.ai.agents.personalisation.schemas import ESPPlatform
from app.ai.agents.skill_loader import extract_skill_for_mode, parse_skill_meta, should_load_skill
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


def build_system_prompt(
    relevant_skills: list[str],
    output_mode: str = "html",
    *,
    remaining_budget: int | None = None,
    client_id: str | None = None,
) -> str:
    """Build system prompt with progressive disclosure of L3 reference files.

    Args:
        relevant_skills: List of skill keys to load.
        output_mode: "html" or "structured" — controls which output format section is included.
        remaining_budget: Optional token budget for skill docs.
        client_id: Optional client org slug for per-client overlay loading.

    Returns:
        Complete system prompt with relevant L3 files appended.
    """
    parts = [_base_system_prompt(output_mode)]

    # Inject eval-informed failure warnings (task 7.2)
    failure_warnings = get_failure_warnings("personalisation")
    if failure_warnings:
        parts.append(f"\n\n{failure_warnings}")

    cumulative_cost = 0
    for skill_key in relevant_skills:
        filename = SKILL_FILES.get(skill_key)
        if filename:
            raw_content = _load_skill_file(filename)
            if raw_content:
                meta, body = parse_skill_meta(raw_content)
                if remaining_budget is not None and not should_load_skill(
                    meta, cumulative_cost, remaining_budget, remaining_budget
                ):
                    continue
                cumulative_cost += meta.token_cost
                parts.append(f"\n\n--- REFERENCE: {skill_key} ---\n\n{body}")

    # Per-client skill overlays (Phase 32.11)
    if client_id:
        from app.ai.agents.skill_loader import apply_overlays, discover_overlays

        overlays = discover_overlays("personalisation", client_id)
        if overlays:
            budget = remaining_budget or 2000
            parts, cumulative_cost, _overlay_names = apply_overlays(
                parts, set(relevant_skills), overlays, cumulative_cost, budget, budget
            )

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
