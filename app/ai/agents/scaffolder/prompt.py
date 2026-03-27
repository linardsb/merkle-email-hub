# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
"""System prompt for the Scaffolder agent.

Thin prompt — core rules only. Detailed patterns loaded from SKILL.md
and skills/*.md via progressive disclosure in the service layer.
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


def build_system_prompt(
    relevant_skills: list[str],
    output_mode: str = "html",
    *,
    remaining_budget: int | None = None,
    client_id: str | None = None,
) -> str:
    """Build system prompt with progressive disclosure of L3 reference files.

    Args:
        relevant_skills: List of skill keys to load (e.g., ['table_layouts', 'maizzle_syntax']).
        output_mode: "html" or "structured" — controls which output format section is included.
        remaining_budget: Optional token budget for skill docs. When set, low-priority
            skills are skipped based on their front matter metadata.
        client_id: Optional client org slug for per-client overlay loading.

    Returns:
        Complete system prompt with relevant L3 files appended.
    """
    parts = [_base_system_prompt(output_mode)]

    # Inject eval-informed failure warnings (task 7.2)
    failure_warnings = get_failure_warnings("scaffolder")
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

        overlays = discover_overlays("scaffolder", client_id)
        if overlays:
            budget = remaining_budget or 2000
            parts, cumulative_cost, _overlay_names = apply_overlays(
                parts, set(relevant_skills), overlays, cumulative_cost, budget, budget
            )

    return "\n".join(parts)


def build_design_context_section(design_context: dict[str, object]) -> str:
    """Build a prompt section from design import context."""
    parts: list[str] = ["## Design Reference (Import)\n"]

    # Structural enforcement for design imports
    parts.append(
        "**CRITICAL — Email HTML structure requirements:**\n"
        '- Use `<table role="presentation">` for ALL structural layout — NEVER `<div>` or `<p>` for layout\n'
        '- Use `<p style="margin:0 0 10px 0;">` for text content inside `<td>` cells '
        "(accessibility — screen readers navigate by paragraphs)\n"
        "- Use `<h1>`-`<h6>` with inline styles for headings inside `<td>` cells "
        "(screen readers scan by headings)\n"
        "- NEVER use `<div>` or `<p>` with layout CSS (width, max-width, display:flex, float)\n"
        '- `<div>` allowed ONLY for: `role="article"` wrapper, MSO hybrid columns '
        "(inside conditionals), simple text-align wrappers inside `<td>`\n"
        "- Multi-column layout: `<table>` with ghost table MSO pattern — NEVER div-based columns\n"
        "- Every section structure: `<table>` > `<tr>` > `<td>` > semantic content "
        "(`<p>`, `<h1>`-`<h6>`, `<a>`, `<img>`)\n"
        "- Spacing: padding on `<td>` only (universal). margin:0 reset on every `<p>` and heading\n"
        "- All styles inline on every element including `font-family` on EVERY `<td>` and heading\n"
        "- MSO conditional wrappers around the 600px container\n"
        '- Main email container: `width="600"` HTML attribute + `max-width:600px` CSS\n'
    )

    layout = design_context.get("layout_summary")
    if layout:
        parts.append(f"**Detected layout:** {layout}\n")

    image_urls = design_context.get("image_urls", {})
    if isinstance(image_urls, dict) and image_urls:
        parts.append(
            "**IMPORTANT — Use these EXACT image URLs in <img> tags. "
            "Do NOT use placeholder URLs (placehold.co, via.placeholder, etc). "
            "These are real images exported from the design:**"
        )
        for node_id, url in image_urls.items():
            parts.append(f"- Section `{node_id}`: `{url}`")
        parts.append("")

    tokens = design_context.get("design_tokens")
    if tokens and isinstance(tokens, dict):
        colors = tokens.get("colors", [])
        if isinstance(colors, list) and colors:
            # Compute palette roles from colors
            from app.design_sync.converter import convert_colors_to_palette
            from app.design_sync.protocol import ExtractedColor

            extracted = [
                ExtractedColor(
                    name=str(c.get("name", "")),
                    hex=str(c.get("hex", "")),
                )
                for c in colors
                if isinstance(c, dict)
            ]
            palette = convert_colors_to_palette(extracted)
            parts.append(
                f"**Color roles (computed from design):**\n"
                f"- Background: `{palette.background}` — use on body/section backgrounds\n"
                f"- Text: `{palette.text}` — use for body copy (MUST contrast with background)\n"
                f"- Primary: `{palette.primary}` — use for headings\n"
                f"- Accent: `{palette.accent}` — use for CTA buttons\n"
                f"- Link: `{palette.link}` — use for hyperlinks\n"
            )

            from app.design_sync.converter import _relative_luminance

            if _relative_luminance(palette.background) < 0.3:
                parts.append(
                    f"\n**DARK BACKGROUND DETECTED — Text color rules:**\n"
                    f"- ALL body text MUST use `{palette.text}` (light color)\n"
                    f"- ALL headings MUST use `{palette.text}` or `#ffffff`\n"
                    "- NEVER use #000000, #111111, #222222, #333333, #444444, #666666\n"
                    "- Links: use light blue (#99ccff) not default blue (#0000ee)\n"
                )

            # Also include raw color list for reference
            color_list = ", ".join(
                f"{c.get('name', '?')}: {c.get('hex', '?')}" for c in colors if isinstance(c, dict)
            )
            parts.append(f"**All brand colors:** {color_list}")
        typography = tokens.get("typography", [])
        if isinstance(typography, list) and typography:
            typo_dicts: list[dict[str, object]] = [t for t in typography if isinstance(t, dict)]
            font_list = ", ".join(
                f"{t.get('name', '?')}: {t.get('family', '?')} {t.get('size', '?')}px"
                for t in typo_dicts
            )
            parts.append(f"**Typography:** {font_list}")
            # Extract primary body and heading fonts for explicit inline instruction
            body_fonts = [
                t
                for t in typo_dicts
                if any(
                    kw in str(t.get("name", "")).lower()
                    for kw in ("body", "text", "paragraph", "regular")
                )
            ]
            heading_fonts = [
                t
                for t in typo_dicts
                if any(
                    kw in str(t.get("name", "")).lower() for kw in ("heading", "title", "h1", "h2")
                )
            ]
            body_family = str(body_fonts[0].get("family", "")) if body_fonts else ""
            heading_family = str(heading_fonts[0].get("family", "")) if heading_fonts else ""
            if body_family or heading_family:
                parts.append(
                    "\n**INLINE FONT REQUIREMENT — Apply these font-family stacks on EVERY element:**"
                )
                if body_family:
                    stack = (
                        f"{body_family}, Arial, Helvetica, sans-serif"
                        if "," not in body_family
                        else body_family
                    )
                    parts.append(f"- Body text `<td>`: `font-family: {stack};`")
                if heading_family:
                    stack = (
                        f"{heading_family}, Arial, Helvetica, sans-serif"
                        if "," not in heading_family
                        else heading_family
                    )
                    parts.append(f"- Headings `<h1>`, `<h2>`: `font-family: {stack};`")
                parts.append(
                    "- Do NOT rely on `<style>` blocks or inheritance — inline on every element"
                )

    source = design_context.get("source_file")
    if source:
        parts.append(f"\n_Source: {source}_")

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
