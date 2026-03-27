"""System prompt for the Accessibility Auditor agent.

Thin prompt — core rules from SKILL.md. Detailed references loaded from
skills/*.md via progressive disclosure based on HTML content analysis.
"""

from pathlib import Path

from app.ai.agents.evals.failure_warnings import get_failure_warnings
from app.ai.agents.skill_loader import extract_skill_for_mode, parse_skill_meta, should_load_skill
from app.ai.agents.skill_override import get_override

_SKILL_DIR = Path(__file__).parent

# Load L1+L2 instructions from SKILL.md (always loaded)
_SKILL_PATH = _SKILL_DIR / "SKILL.md"
_SKILL_CONTENT = _SKILL_PATH.read_text(encoding="utf-8") if _SKILL_PATH.exists() else ""

_PROMPT_PREFIX = """\
You are an expert email accessibility auditor specialising in WCAG 2.1 AA
compliance for HTML email. Your sole task is to audit and fix accessibility
issues in email HTML while preserving visual design.
"""


def _load_skill_file(name: str) -> str:
    """Load an L3 skill reference file by name."""
    path = _SKILL_DIR / "skills" / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


# L3 reference files — loaded on demand by detect_relevant_skills()
SKILL_FILES: dict[str, str] = {
    "wcag_email_mapping": "wcag_email_mapping.md",
    "alt_text_guidelines": "alt_text_guidelines.md",
    "color_contrast": "color_contrast.md",
    "screen_reader_behavior": "screen_reader_behavior.md",
}


def _base_system_prompt(output_mode: str = "html") -> str:
    """Build base system prompt with output-mode-aware section extraction."""
    skill = get_override("accessibility") or _SKILL_CONTENT
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
    failure_warnings = get_failure_warnings("accessibility")
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

        overlays = discover_overlays("accessibility", client_id)
        if overlays:
            budget = remaining_budget or 2000
            parts, cumulative_cost, _overlay_names = apply_overlays(
                parts, set(relevant_skills), overlays, cumulative_cost, budget, budget
            )

    return "\n".join(parts)


def detect_relevant_skills(html: str, focus_areas: list[str] | None = None) -> list[str]:
    """Detect which L3 skill files are relevant based on HTML content.

    Progressive disclosure — only load skill files for detected issues.

    Args:
        html: Input email HTML to analyze.
        focus_areas: Optional explicit list of audit areas.

    Returns:
        List of relevant skill keys.
    """
    html_lower = html.lower()
    skills: list[str] = []

    # Always load WCAG mapping for comprehensive reference
    skills.append("wcag_email_mapping")

    if focus_areas:
        # Explicit focus areas — load matching skills
        area_set = {a.lower() for a in focus_areas}
        if area_set & {"alt_text", "alt", "images", "img"}:
            skills.append("alt_text_guidelines")
        if area_set & {"contrast", "color", "colors", "colour"}:
            skills.append("color_contrast")
        if area_set & {"screen_reader", "aria", "sr", "voiceover", "nvda", "jaws"}:
            skills.append("screen_reader_behavior")
    else:
        # Auto-detect from HTML content
        if "<img" in html_lower:
            skills.append("alt_text_guidelines")

        # Load contrast guide if inline color styles detected
        if "color:" in html_lower or "background-color:" in html_lower:
            skills.append("color_contrast")

        # Load screen reader guide if tables, VML, or ARIA present
        if (
            "<table" in html_lower
            or "<v:" in html_lower
            or "aria-" in html_lower
            or "role=" in html_lower
        ):
            skills.append("screen_reader_behavior")

    return list(dict.fromkeys(skills))  # deduplicate preserving order
