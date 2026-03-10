"""Progressive disclosure prompt builder for the Innovation agent."""

from pathlib import Path

from app.ai.agents.evals.failure_warnings import get_failure_warnings
from app.ai.agents.skill_override import get_override
from app.core.logging import get_logger

logger = get_logger(__name__)

_AGENT_DIR = Path(__file__).parent

# L3 skill files loaded on-demand
SKILL_FILES: dict[str, str] = {
    "css_checkbox_hacks": "css_checkbox_hacks.md",
    "amp_email": "amp_email.md",
    "css_animations": "css_animations.md",
    "feasibility_framework": "feasibility_framework.md",
    "competitive_landscape": "competitive_landscape.md",
}


def detect_relevant_skills(technique: str) -> list[str]:
    """Detect which L3 skills are relevant to the technique request."""
    t = technique.lower()
    relevant: list[str] = []

    # Always load feasibility framework (core to Innovation agent)
    relevant.append("feasibility_framework")

    # Interactive / checkbox hack techniques
    checkbox_keywords = [
        "tab",
        "accordion",
        "carousel",
        "toggle",
        "checkbox",
        "hamburger",
        "menu",
        "interactive",
        "collapsible",
        "drawer",
    ]
    if any(kw in t for kw in checkbox_keywords):
        relevant.append("css_checkbox_hacks")

    # AMP for Email
    amp_keywords = [
        "amp",
        "dynamic",
        "form",
        "real-time",
        "live",
        "carousel amp",
        "accordion amp",
        "interactive form",
    ]
    if any(kw in t for kw in amp_keywords):
        relevant.append("amp_email")

    # Animations and transitions
    animation_keywords = [
        "animation",
        "animate",
        "transition",
        "hover",
        "keyframe",
        "transform",
        "fade",
        "slide",
        "bounce",
        "spin",
        "pulse",
        "shake",
    ]
    if any(kw in t for kw in animation_keywords):
        relevant.append("css_animations")

    # Competitive landscape
    competitive_keywords = [
        "competitor",
        "alternative",
        "stripo",
        "parcel",
        "chamaileon",
        "dyspatch",
        "knak",
        "differentiate",
        "unique",
        "advantage",
        "gap",
        "landscape",
    ]
    if any(kw in t for kw in competitive_keywords):
        relevant.append("competitive_landscape")

    return relevant


def build_system_prompt(relevant_skills: list[str]) -> str:
    """Build system prompt from SKILL.md + relevant L3 files."""
    override = get_override("innovation")
    if override is not None:
        base_prompt = override
    else:
        skill_path = _AGENT_DIR / "SKILL.md"
        base_prompt = skill_path.read_text()

    # Inject eval-informed failure warnings (task 7.2)
    failure_warnings = get_failure_warnings("innovation")
    if failure_warnings:
        base_prompt += f"\n\n{failure_warnings}"

    for skill_name in relevant_skills:
        filename = SKILL_FILES.get(skill_name)
        if not filename:
            continue
        skill_file = _AGENT_DIR / "skills" / filename
        if skill_file.exists():
            content = skill_file.read_text()
            base_prompt += f"\n\n---\n## Reference: {skill_name}\n\n{content}"
            logger.info(
                "agents.innovation.skill_loaded",
                skill=skill_name,
            )

    return base_prompt
