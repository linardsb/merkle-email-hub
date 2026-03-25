"""Visual QA agent prompt construction and skill detection."""

from __future__ import annotations

from pathlib import Path

from app.ai.agents.skill_loader import parse_skill_meta

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
# No L3 files yet; add entries as skill files are created.
SKILL_FILES: dict[str, str] = {}


def build_system_prompt(
    relevant_skills: list[str],
    output_mode: str = "structured",  # noqa: ARG001
) -> str:
    """Build system prompt for visual QA analysis."""
    base = (
        "You are a Visual QA agent specialising in email rendering analysis.\n\n"
        "You receive screenshots of the same email rendered across different email clients "
        "(Gmail, Outlook, Apple Mail, etc.) and the original HTML source.\n\n"
        "Your task:\n"
        "1. Compare the screenshots to identify rendering defects — layout breaks, "
        "missing elements, color inversions, text overflow, image sizing issues, "
        "clipped content, collapsed columns, misaligned elements.\n"
        "2. For each defect, identify the CSS property causing it and suggest a concrete fix.\n"
        "3. Rate overall rendering quality (0.0 = completely broken, 1.0 = pixel-perfect).\n"
        "4. Flag which clients have critical rendering issues.\n\n"
        "Return your analysis as JSON with fields:\n"
        "- defects: array of {region, description, severity, affected_clients, "
        "suggested_fix, css_property}\n"
        "- overall_rendering_score: float 0-1\n"
        "- critical_clients: array of client names with critical issues\n"
        "- summary: one-paragraph summary\n"
        "- confidence: float 0-1\n"
        "- auto_fixable: boolean — true if all defects have concrete CSS fixes\n\n"
        "Severity levels:\n"
        "- critical: Content is missing, unreadable, or layout is broken\n"
        "- warning: Visual degradation but content remains usable\n"
        "- info: Minor cosmetic differences expected across clients\n"
    )

    # Append L1+L2 from SKILL.md
    if _SKILL_CONTENT:
        _meta, body = parse_skill_meta(_SKILL_CONTENT)
        base += f"\n\n{body}"

    # Append relevant L3 skill files
    for skill_key in relevant_skills:
        filename = SKILL_FILES.get(skill_key)
        if filename:
            content = _load_skill_file(filename)
            if content:
                base += f"\n\n## Skill: {skill_key}\n{content}"

    return base


def detect_relevant_skills(html: str) -> list[str]:
    """Detect which L3 skill files to load based on HTML content.

    Currently no L3 skill files exist — returns empty list.
    As skill files are added to SKILL_FILES, detection logic will be enabled.
    """
    if not SKILL_FILES:
        return []

    relevant: list[str] = []
    html_lower = html.lower()
    for skill_key in SKILL_FILES:
        if ("mso" in skill_key and ("mso-" in html_lower or "<!--[if" in html_lower)) or ("dark" in skill_key and (
            "prefers-color-scheme" in html_lower or "data-ogsc" in html_lower
        )) or "layout" in skill_key:
            relevant.append(skill_key)
    return relevant
