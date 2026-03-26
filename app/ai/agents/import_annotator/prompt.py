"""Import annotator agent prompt."""

from pathlib import Path

from app.ai.agents.evals.failure_warnings import get_failure_warnings
from app.ai.agents.skill_loader import extract_skill_for_mode
from app.ai.agents.skill_override import get_override

_SKILL_DIR = Path(__file__).parent
_SKILL_PATH = _SKILL_DIR / "SKILL.md"
_SKILL_CONTENT = _SKILL_PATH.read_text(encoding="utf-8") if _SKILL_PATH.exists() else ""

SKILL_FILES: dict[str, str] = {
    "table_layouts": "skills/table_layouts.md",
    "div_layouts": "skills/div_layouts.md",
    "esp_tokens": "skills/esp_tokens.md",
    "column_patterns": "skills/column_patterns.md",
    "common_email_builders": "skills/l3/common_email_builders.md",
    "css_normalization": "skills/l3/css_normalization.md",
    "wrapper_detection": "skills/l3/wrapper_detection.md",
    "esp_token_edge_cases": "skills/l3/esp_token_edge_cases.md",
}


def _base_system_prompt(output_mode: str = "html") -> str:
    override = get_override("import_annotator")
    if override:
        return override
    return extract_skill_for_mode(_SKILL_CONTENT, output_mode)


def detect_relevant_skills(html: str, esp_platform: str | None = None) -> list[str]:
    """Detect which L3 skills to load based on HTML content."""
    skills: list[str] = []
    html_lower = html.lower()

    # Always load ESP tokens if any ESP syntax detected
    esp_markers = ["{{", "{%", "%%[", "%%=", "<%", "#if("]
    if any(m in html for m in esp_markers):
        skills.append("esp_tokens")

    # Table layouts if tables present
    if "<table" in html_lower:
        skills.append("table_layouts")

    # Div layouts if modern structure
    if "mj-column" in html_lower or "email-body" in html_lower or "wrapper" in html_lower:
        skills.append("div_layouts")

    # Column patterns
    col_markers = ["inline-block", "float:", "calc(", "mj-column-per"]
    if any(m in html_lower for m in col_markers):
        skills.append("column_patterns")

    # If ESP platform specified, always load esp_tokens
    if esp_platform and "esp_tokens" not in skills:
        skills.append("esp_tokens")

    # Email builder detection (Stripo, Bee Free, Mailchimp, MJML, Litmus)
    builder_markers = ["esd-", "bee-", "mc:edit", "stripo", "<!-- begin module", "<!-- module:"]
    if any(m in html_lower for m in builder_markers):
        skills.append("common_email_builders")

    # CSS normalization (high !important count or vendor prefixes)
    if html_lower.count("!important") > 5 or "-webkit-" in html_lower or "-moz-" in html_lower:
        skills.append("css_normalization")

    # Wrapper detection — always load (core to import fidelity)
    skills.append("wrapper_detection")

    # ESP edge cases (advanced token patterns, Mailchimp merge tags)
    esp_edge_markers = [
        "*|",
        "%%=concat",
        "%%=redirect",
        "{{{",
        "{{>",
        "{% connected_content",
        "<%- include",
    ]
    if any(m in html_lower for m in esp_edge_markers):
        skills.append("esp_token_edge_cases")

    # For very large HTML, load everything
    if len(html) > 50_000:
        skills = list(SKILL_FILES.keys())

    return list(dict.fromkeys(skills))


def build_system_prompt(
    relevant_skills: list[str],
    output_mode: str = "html",
) -> str:
    """Build the full system prompt with relevant L3 skills appended."""
    prompt = _base_system_prompt(output_mode)

    # Append failure warnings from eval analysis
    warnings = get_failure_warnings("import_annotator")
    if warnings:
        prompt += f"\n\n## KNOWN FAILURE PATTERNS\n{warnings}"

    # Append relevant L3 skill files
    for key in relevant_skills:
        if key in SKILL_FILES:
            path = _SKILL_DIR / SKILL_FILES[key]
            if path.exists():
                content = path.read_text(encoding="utf-8")
                prompt += f"\n\n--- REFERENCE: {key} ---\n{content}"

    return prompt
