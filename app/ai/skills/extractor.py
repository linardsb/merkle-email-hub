"""Deterministic pattern extraction from email template HTML.

8 detector functions analyze HTML for email development patterns
(VML, MSO conditionals, dark mode, responsive, accessibility, ESP syntax,
performance, progressive enhancement). All use regex + lxml — no LLM.
"""

from __future__ import annotations

import re

from lxml import html as lxml_html

from app.ai.skills.schemas import PatternCategory, SkillPattern
from app.core.logging import get_logger

logger = get_logger(__name__)

# --- Compiled regex patterns ---

_VML_ROUNDRECT_RE = re.compile(r"<v:roundrect\b[^>]*>.*?</v:roundrect>", re.IGNORECASE | re.DOTALL)
_VML_RECT_RE = re.compile(r"<v:rect\b[^>]*>.*?</v:rect>", re.IGNORECASE | re.DOTALL)
_VML_OVAL_RE = re.compile(r"<v:oval\b[^>]*>.*?</v:oval>", re.IGNORECASE | re.DOTALL)
_VML_FILL_RE = re.compile(r"<v:fill\b[^>]*/>", re.IGNORECASE)
_VML_TEXTBOX_RE = re.compile(r"<v:textbox\b[^>]*>.*?</v:textbox>", re.IGNORECASE | re.DOTALL)
_VML_NS_RE = re.compile(r'xmlns:v="urn:schemas-microsoft-com:vml"', re.IGNORECASE)

_MSO_COND_RE = re.compile(r"<!--\[if\s+([^\]]*(?:mso|IE)[^\]]*)\]>", re.IGNORECASE)
_MSO_DPI_RE = re.compile(r"mso-dpi-\w+", re.IGNORECASE)
_GHOST_TABLE_RE = re.compile(r"<!--\[if\s[^\]]*mso[^\]]*\]>\s*<table", re.IGNORECASE | re.DOTALL)

_PREFERS_COLOR_SCHEME_RE = re.compile(
    r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)", re.IGNORECASE
)
_DATA_OGSC_RE = re.compile(r"\[data-ogsc\]", re.IGNORECASE)
_DATA_OGSB_RE = re.compile(r"\[data-ogsb\]", re.IGNORECASE)
_COLOR_SCHEME_META_RE = re.compile(r'<meta\s[^>]*name="color-scheme"[^>]*/?>', re.IGNORECASE)

_MEDIA_QUERY_RE = re.compile(r"@media\s*[^{]*max-width\s*:\s*(\d+)px", re.IGNORECASE)
_FLUID_WIDTH_RE = re.compile(r"width\s*:\s*100%", re.IGNORECASE)
_MAX_WIDTH_CONTAINER_RE = re.compile(r"max-width\s*:\s*(\d+)px", re.IGNORECASE)

_ROLE_PRESENTATION_RE = re.compile(r'role="presentation"', re.IGNORECASE)
_ARIA_LABEL_RE = re.compile(r'aria-label="[^"]*"', re.IGNORECASE)
_LANG_ATTR_RE = re.compile(r'<html[^>]+lang="[^"]*"', re.IGNORECASE)
_SCOPE_ATTR_RE = re.compile(r'scope="(row|col)"', re.IGNORECASE)

_LIQUID_RE = re.compile(r"\{%\s*(if|for|case|unless)\b", re.IGNORECASE)
_AMPSCRIPT_RE = re.compile(r"%%\[.*?\]%%", re.DOTALL)
_MERGE_TAG_RE = re.compile(r"\*\|[A-Z_]+\|\*")
_HANDLEBARS_RE = re.compile(r"\{\{#(if|each|unless)\b")

_DISPLAY_NONE_RE = re.compile(
    r'display\s*:\s*none[^"]*"[^>]*>[^<]*preheader', re.IGNORECASE | re.DOTALL
)

_FLEXBOX_RE = re.compile(r"display\s*:\s*flex", re.IGNORECASE)
_GRID_RE = re.compile(r"display\s*:\s*grid", re.IGNORECASE)
_TABLE_FALLBACK_RE = re.compile(r"<!--\[if\s[^\]]*mso[^\]]*\]>.*?<table", re.IGNORECASE | re.DOTALL)
_BG_IMAGE_RE = re.compile(r"background-image\s*:", re.IGNORECASE)


def extract_patterns(html: str, source_template_id: str | None = None) -> list[SkillPattern]:
    """Extract all detectable email development patterns from HTML.

    Args:
        html: Raw email HTML to analyze.
        source_template_id: Optional ID for traceability.

    Returns:
        List of detected patterns sorted by confidence (descending).
    """
    patterns: list[SkillPattern] = []
    kwargs = {"source_template_id": source_template_id}

    for detector in _DETECTORS:
        try:
            patterns.extend(detector(html, **kwargs))
        except Exception:
            logger.warning(
                "skill_extractor.detector_failed",
                detector=detector.__name__,
                exc_info=True,
            )

    patterns.sort(key=lambda p: p.confidence, reverse=True)
    return patterns


def detect_vml_patterns(html: str, *, source_template_id: str | None = None) -> list[SkillPattern]:
    """Detect VML shapes, fills, textboxes used for Outlook rendering."""
    results: list[SkillPattern] = []

    # VML Roundrect (bulletproof buttons)
    matches = _VML_ROUNDRECT_RE.findall(html)
    if matches:
        results.append(
            SkillPattern(
                pattern_name="vml_bulletproof_button",
                category=PatternCategory.OUTLOOK_FIX,
                description="VML v:roundrect for bulletproof CTA buttons in Outlook desktop",
                html_example=_truncate(matches[0], 500),
                confidence=0.95,
                source_template_id=source_template_id,
                applicable_agents=["outlook_fixer"],
            )
        )

    # VML Rect (background images)
    matches = _VML_RECT_RE.findall(html)
    if matches and _VML_FILL_RE.search(html):
        results.append(
            SkillPattern(
                pattern_name="vml_background_image",
                category=PatternCategory.OUTLOOK_FIX,
                description="VML v:rect with v:fill for Outlook background images",
                html_example=_truncate(matches[0], 500),
                confidence=0.95,
                source_template_id=source_template_id,
                applicable_agents=["outlook_fixer", "scaffolder"],
            )
        )

    # VML Oval
    oval_matches = _VML_OVAL_RE.findall(html)
    if oval_matches:
        results.append(
            SkillPattern(
                pattern_name="vml_oval_shape",
                category=PatternCategory.OUTLOOK_FIX,
                description="VML v:oval for circular shapes in Outlook desktop",
                html_example=_truncate(oval_matches[0], 300),
                confidence=0.85,
                source_template_id=source_template_id,
                applicable_agents=["outlook_fixer"],
            )
        )

    # VML namespace declaration
    if _VML_NS_RE.search(html) and not results:
        results.append(
            SkillPattern(
                pattern_name="vml_namespace_usage",
                category=PatternCategory.OUTLOOK_FIX,
                description="VML XML namespace declared — template uses VML elements",
                html_example='xmlns:v="urn:schemas-microsoft-com:vml"',
                confidence=0.5,
                source_template_id=source_template_id,
                applicable_agents=["outlook_fixer"],
            )
        )

    return results


def detect_mso_conditionals(
    html: str, *, source_template_id: str | None = None
) -> list[SkillPattern]:
    """Detect MSO conditional comments, ghost tables, DPI scaling."""
    results: list[SkillPattern] = []

    cond_matches = _MSO_COND_RE.findall(html)
    if not cond_matches:
        return results

    # Unique version targets
    version_targets = {m.strip().lower() for m in cond_matches}

    # Ghost tables
    ghost_matches = _GHOST_TABLE_RE.findall(html)
    if ghost_matches:
        results.append(
            SkillPattern(
                pattern_name="mso_ghost_table",
                category=PatternCategory.OUTLOOK_FIX,
                description=f"MSO ghost tables for Outlook layout control ({len(ghost_matches)} found)",
                html_example=_truncate(ghost_matches[0], 400),
                confidence=0.9,
                source_template_id=source_template_id,
                applicable_agents=["outlook_fixer", "scaffolder"],
            )
        )

    # DPI scaling patterns
    if _MSO_DPI_RE.search(html):
        results.append(
            SkillPattern(
                pattern_name="mso_dpi_scaling",
                category=PatternCategory.OUTLOOK_FIX,
                description="MSO DPI scaling properties for high-DPI Outlook rendering",
                html_example="mso-dpi-x / mso-dpi-y",
                confidence=0.85,
                source_template_id=source_template_id,
                applicable_agents=["outlook_fixer"],
            )
        )

    # Version-specific targeting
    specific_versions = [
        t
        for t in version_targets
        if any(v in t for v in ("gte mso 9", "gte mso 12", "mso 15", "mso 16", "!mso"))
    ]
    if specific_versions:
        results.append(
            SkillPattern(
                pattern_name="mso_version_targeting",
                category=PatternCategory.OUTLOOK_FIX,
                description=f"MSO version-specific conditionals: {', '.join(sorted(specific_versions)[:5])}",
                html_example=f"<!--[if {specific_versions[0]}]>...<![endif]-->",
                confidence=0.9,
                source_template_id=source_template_id,
                applicable_agents=["outlook_fixer", "scaffolder"],
            )
        )

    return results


def detect_dark_mode_patterns(
    html: str, *, source_template_id: str | None = None
) -> list[SkillPattern]:
    """Detect prefers-color-scheme, Outlook dark mode selectors, color-scheme meta."""
    results: list[SkillPattern] = []

    has_pcs = bool(_PREFERS_COLOR_SCHEME_RE.search(html))
    has_ogsc = bool(_DATA_OGSC_RE.search(html))
    has_ogsb = bool(_DATA_OGSB_RE.search(html))
    has_meta = bool(_COLOR_SCHEME_META_RE.search(html))

    if has_pcs:
        results.append(
            SkillPattern(
                pattern_name="dark_mode_media_query",
                category=PatternCategory.DARK_MODE,
                description="prefers-color-scheme: dark media query for dark mode support",
                html_example="@media (prefers-color-scheme: dark) { ... }",
                confidence=0.95,
                source_template_id=source_template_id,
                applicable_agents=["dark_mode"],
            )
        )

    if has_ogsc or has_ogsb:
        selectors = []
        if has_ogsc:
            selectors.append("[data-ogsc]")
        if has_ogsb:
            selectors.append("[data-ogsb]")
        results.append(
            SkillPattern(
                pattern_name="outlook_dark_mode_selectors",
                category=PatternCategory.DARK_MODE,
                description=f"Outlook-specific dark mode selectors: {', '.join(selectors)}",
                html_example=f"{selectors[0]} .dark-img {{ display: block !important; }}",
                confidence=0.95,
                source_template_id=source_template_id,
                applicable_agents=["dark_mode"],
            )
        )

    if has_meta:
        results.append(
            SkillPattern(
                pattern_name="color_scheme_meta",
                category=PatternCategory.DARK_MODE,
                description='<meta name="color-scheme"> for dark mode opt-in',
                html_example='<meta name="color-scheme" content="light dark">',
                confidence=0.9,
                source_template_id=source_template_id,
                applicable_agents=["dark_mode", "scaffolder"],
            )
        )

    return results


def detect_responsive_patterns(
    html: str, *, source_template_id: str | None = None
) -> list[SkillPattern]:
    """Detect fluid widths, max-width containers, breakpoint media queries."""
    results: list[SkillPattern] = []

    breakpoints = _MEDIA_QUERY_RE.findall(html)
    if breakpoints:
        bp_values = sorted(set(breakpoints))
        results.append(
            SkillPattern(
                pattern_name="responsive_breakpoints",
                category=PatternCategory.RESPONSIVE,
                description=f"Responsive breakpoints at: {', '.join(bp_values[:5])}px",
                html_example=f"@media (max-width: {bp_values[0]}px) {{ ... }}",
                confidence=0.85,
                source_template_id=source_template_id,
                applicable_agents=["scaffolder"],
            )
        )

    try:
        doc = lxml_html.document_fromstring(html)
        fluid_tables = doc.xpath(
            '//table[contains(@style, "width:100%") '
            'or contains(@style, "width: 100%") '
            'or @width="100%"]'
        )
        max_width_els = doc.xpath('//*[contains(@style, "max-width")]')
        if fluid_tables and max_width_els:
            results.append(
                SkillPattern(
                    pattern_name="fluid_width_with_max_constraint",
                    category=PatternCategory.RESPONSIVE,
                    description=(
                        f"Fluid-width tables ({len(fluid_tables)}) "
                        f"with max-width constraints ({len(max_width_els)})"
                    ),
                    html_example='<table width="100%" style="max-width:600px">',
                    confidence=0.8,
                    source_template_id=source_template_id,
                    applicable_agents=["scaffolder"],
                )
            )
    except Exception:
        logger.debug("skill_extractor.lxml_parse_failed", exc_info=True)

    return results


def detect_accessibility_patterns(
    html: str, *, source_template_id: str | None = None
) -> list[SkillPattern]:
    """Detect role=presentation, aria-label, lang, heading hierarchy, scope."""
    results: list[SkillPattern] = []

    role_count = len(_ROLE_PRESENTATION_RE.findall(html))
    aria_count = len(_ARIA_LABEL_RE.findall(html))
    has_lang = bool(_LANG_ATTR_RE.search(html))
    scope_count = len(_SCOPE_ATTR_RE.findall(html))

    if role_count >= 3:
        results.append(
            SkillPattern(
                pattern_name="layout_table_roles",
                category=PatternCategory.ACCESSIBILITY,
                description=f'role="presentation" on {role_count} layout tables',
                html_example='<table role="presentation">',
                confidence=0.9,
                source_template_id=source_template_id,
                applicable_agents=["accessibility"],
            )
        )

    if aria_count >= 2:
        results.append(
            SkillPattern(
                pattern_name="aria_labels_on_links",
                category=PatternCategory.ACCESSIBILITY,
                description=f"aria-label attributes on {aria_count} elements",
                html_example='<a href="..." aria-label="Shop now">',
                confidence=0.85,
                source_template_id=source_template_id,
                applicable_agents=["accessibility"],
            )
        )

    if has_lang:
        results.append(
            SkillPattern(
                pattern_name="html_lang_attribute",
                category=PatternCategory.ACCESSIBILITY,
                description="lang attribute on <html> element for screen readers",
                html_example='<html lang="en">',
                confidence=0.9,
                source_template_id=source_template_id,
                applicable_agents=["accessibility", "scaffolder"],
            )
        )

    if scope_count >= 1:
        results.append(
            SkillPattern(
                pattern_name="table_scope_attributes",
                category=PatternCategory.ACCESSIBILITY,
                description=f"scope attributes on {scope_count} table headers",
                html_example='<th scope="col">',
                confidence=0.8,
                source_template_id=source_template_id,
                applicable_agents=["accessibility"],
            )
        )

    return results


def detect_esp_patterns(html: str, *, source_template_id: str | None = None) -> list[SkillPattern]:
    """Detect Liquid, AMPscript, merge tags, Handlebars control flow."""
    results: list[SkillPattern] = []

    liquid_matches = _LIQUID_RE.findall(html)
    if liquid_matches:
        tags = sorted({m.lower() for m in liquid_matches})
        results.append(
            SkillPattern(
                pattern_name="liquid_control_flow",
                category=PatternCategory.ESP_SYNTAX,
                description=f"Liquid template tags: {', '.join(tags)}",
                html_example="{%% if subscriber.first_name %%}...{%% endif %%}",
                confidence=0.9,
                source_template_id=source_template_id,
                applicable_agents=["personalisation"],
            )
        )

    if _AMPSCRIPT_RE.search(html):
        results.append(
            SkillPattern(
                pattern_name="ampscript_syntax",
                category=PatternCategory.ESP_SYNTAX,
                description="SFMC AMPscript expressions (%%[...]%%)",
                html_example="%%[SET @name = AttributeValue('FirstName')]%%",
                confidence=0.9,
                source_template_id=source_template_id,
                applicable_agents=["personalisation"],
            )
        )

    if _MERGE_TAG_RE.search(html):
        results.append(
            SkillPattern(
                pattern_name="merge_tag_syntax",
                category=PatternCategory.ESP_SYNTAX,
                description="Mailchimp-style merge tags (*|FIELD|*)",
                html_example="*|FNAME|*",
                confidence=0.85,
                source_template_id=source_template_id,
                applicable_agents=["personalisation"],
            )
        )

    hb_matches = _HANDLEBARS_RE.findall(html)
    if hb_matches:
        results.append(
            SkillPattern(
                pattern_name="handlebars_control_flow",
                category=PatternCategory.ESP_SYNTAX,
                description=f"Handlebars block helpers: {', '.join(sorted(set(hb_matches)))}",
                html_example="{{#if user.premium}}...{{/if}}",
                confidence=0.85,
                source_template_id=source_template_id,
                applicable_agents=["personalisation"],
            )
        )

    return results


def detect_performance_patterns(
    html: str, *, source_template_id: str | None = None
) -> list[SkillPattern]:
    """Detect preheader hide, Gmail-safe classes, size optimization patterns."""
    results: list[SkillPattern] = []

    if _DISPLAY_NONE_RE.search(html):
        results.append(
            SkillPattern(
                pattern_name="hidden_preheader",
                category=PatternCategory.PERFORMANCE,
                description="display:none preheader text for preview text control",
                html_example='<div style="display:none;max-height:0;overflow:hidden;">Preheader</div>',
                confidence=0.9,
                source_template_id=source_template_id,
                applicable_agents=["code_reviewer", "scaffolder"],
            )
        )

    # Check file size as a signal of optimization awareness
    html_size = len(html.encode("utf-8"))
    if html_size > 100_000:
        results.append(
            SkillPattern(
                pattern_name="large_template_size",
                category=PatternCategory.PERFORMANCE,
                description=f"Template is {html_size // 1024}KB — may need optimization",
                html_example="(size signal, no HTML example)",
                confidence=0.6,
                source_template_id=source_template_id,
                applicable_agents=["code_reviewer"],
            )
        )

    return results


def detect_progressive_enhancement(
    html: str, *, source_template_id: str | None = None
) -> list[SkillPattern]:
    """Detect flexbox/grid with table fallback, bg-image with VML rect."""
    results: list[SkillPattern] = []

    has_flexbox = bool(_FLEXBOX_RE.search(html))
    has_grid = bool(_GRID_RE.search(html))
    has_table_fallback = bool(_TABLE_FALLBACK_RE.search(html))

    if (has_flexbox or has_grid) and has_table_fallback:
        modern: list[str] = []
        if has_flexbox:
            modern.append("flexbox")
        if has_grid:
            modern.append("CSS grid")
        results.append(
            SkillPattern(
                pattern_name="progressive_css_with_table_fallback",
                category=PatternCategory.PROGRESSIVE_ENHANCEMENT,
                description=f"Progressive enhancement: {' + '.join(modern)} with MSO table fallback",
                html_example="display:flex → <!--[if mso]><table>...<![endif]-->",
                confidence=0.9,
                source_template_id=source_template_id,
                applicable_agents=["scaffolder", "outlook_fixer"],
            )
        )

    # Background image with VML rect fallback
    has_bg_image = bool(_BG_IMAGE_RE.search(html))
    has_vml_rect = bool(_VML_RECT_RE.search(html))
    if has_bg_image and has_vml_rect:
        results.append(
            SkillPattern(
                pattern_name="bg_image_vml_fallback",
                category=PatternCategory.PROGRESSIVE_ENHANCEMENT,
                description="CSS background-image with VML v:rect fallback for Outlook",
                html_example="background-image:url(...) → <v:rect><v:fill type='frame'/>",
                confidence=0.9,
                source_template_id=source_template_id,
                applicable_agents=["scaffolder", "outlook_fixer"],
            )
        )

    return results


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len, adding ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


# Registry of all detector functions
_DETECTORS = [
    detect_vml_patterns,
    detect_mso_conditionals,
    detect_dark_mode_patterns,
    detect_responsive_patterns,
    detect_accessibility_patterns,
    detect_esp_patterns,
    detect_performance_patterns,
    detect_progressive_enhancement,
]
