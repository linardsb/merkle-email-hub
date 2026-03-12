# ruff: noqa: ARG001
"""Custom check functions for rules too complex for declarative YAML.

Each function follows the CustomCheckFn protocol:
    (doc, raw_html, config) -> (issues: list[str], deduction: float)

The deduction returned is the TOTAL deduction (not per-issue) — the function
handles its own per-element counting and capping internally.
"""

from __future__ import annotations

import json
import re
from collections import Counter

from lxml.html import HtmlElement

from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.rule_engine import register_custom_check

# --- Constants ---

_BLOCK_TAGS = frozenset(
    {
        "div",
        "table",
        "tr",
        "td",
        "th",
        "p",
        "section",
        "header",
        "footer",
        "thead",
        "tbody",
        "tfoot",
        "ul",
        "ol",
        "li",
        "blockquote",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "article",
        "aside",
        "nav",
        "main",
        "figure",
        "figcaption",
        "details",
        "summary",
        "fieldset",
    }
)

_INLINE_TAGS = frozenset(
    {
        "a",
        "span",
        "strong",
        "em",
        "b",
        "i",
        "u",
        "s",
        "small",
        "mark",
        "del",
        "ins",
        "sub",
        "sup",
        "abbr",
        "cite",
        "q",
        "time",
        "data",
        "code",
        "label",
    }
)

_TABLE_VALID_PARENTS: dict[str, frozenset[str]] = {
    "td": frozenset({"tr"}),
    "th": frozenset({"tr"}),
    "tr": frozenset({"table", "thead", "tbody", "tfoot"}),
    "thead": frozenset({"table"}),
    "tbody": frozenset({"table"}),
    "tfoot": frozenset({"table"}),
    "caption": frozenset({"table"}),
    "colgroup": frozenset({"table"}),
    "col": frozenset({"colgroup", "table"}),
}

_SELF_CLOSING_TAGS = frozenset(
    {
        "br",
        "hr",
        "img",
        "input",
        "meta",
        "link",
        "area",
        "base",
        "col",
        "embed",
        "source",
        "track",
        "wbr",
    }
)

# --- Default deductions (match defaults.yaml) ---

_DEFAULTS: dict[str, float | int] = {
    "deduction_doctype": 0.15,
    "deduction_structure": 0.15,
    "deduction_charset": 0.15,
    "deduction_viewport": 0.10,
    "deduction_title": 0.10,
    "deduction_unclosed_tag": 0.15,
    "deduction_nesting": 0.10,
    "deduction_duplicate_id": 0.10,
    "deduction_empty_section": 0.15,
    "deduction_style_placement": 0.10,
    "deduction_table_structure": 0.15,
    "deduction_list_structure": 0.10,
    "deduction_duplicate_structural": 0.15,
    "deduction_nested_link": 0.15,
    "deduction_missing_fallback": 0.10,
    "deduction_interactive_structure": 0.10,
    "deduction_dangerous_element": 0.15,
    "max_unclosed_tags_reported": 5,
    "max_nesting_violations_reported": 5,
    "max_duplicate_ids_reported": 5,
    "max_table_violations_reported": 5,
    "max_list_violations_reported": 5,
}


def _param(config: QACheckConfig | None, key: str) -> float | int:
    """Get a config param with fallback to default."""
    if config:
        val: float | int = config.params.get(key, _DEFAULTS[key])
        return val
    return _DEFAULTS[key]


# --- Tag counting helpers ---

_TAG_PATTERNS: dict[str, tuple[re.Pattern[str], re.Pattern[str], re.Pattern[str]]] = {}


def _get_tag_patterns(
    tag: str,
) -> tuple[re.Pattern[str], re.Pattern[str], re.Pattern[str]]:
    """Get pre-compiled regex patterns for a tag name (cached)."""
    if tag not in _TAG_PATTERNS:
        _TAG_PATTERNS[tag] = (
            re.compile(rf"<{tag}[\s/>]", re.IGNORECASE),
            re.compile(rf"</{tag}\s*>", re.IGNORECASE),
            re.compile(rf"<{tag}\b[^>]*/\s*>", re.IGNORECASE),
        )
    return _TAG_PATTERNS[tag]


def _count_raw_tags(raw_html: str, tag: str) -> tuple[int, int]:
    """Count opening and closing tags in raw HTML (case-insensitive).

    Returns (open_count, close_count). Handles self-closing and attributes.
    """
    open_pattern, close_pattern, self_close_pattern = _get_tag_patterns(tag)

    opens = len(open_pattern.findall(raw_html))
    self_closes = len(self_close_pattern.findall(raw_html))
    closes = len(close_pattern.findall(raw_html))

    return opens - self_closes, closes


# ---------------------------------------------------------------------------
# Custom check functions — extracted from html_validation.py
# ---------------------------------------------------------------------------


def check_html_structure(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 2: <html> wraps <head> + <body>."""
    deduction = float(_param(config, "deduction_structure"))
    issues: list[str] = []
    total = 0.0

    raw_lower = raw_html.lower()
    if "<html" not in raw_lower:
        issues.append("Missing <html> tag")
        total += deduction
        return issues, total

    if not doc.findall(".//head"):
        issues.append("Missing <head> section")
        total += deduction

    if not doc.findall(".//body"):
        issues.append("Missing <body> section")
        total += deduction

    return issues, total


def check_charset(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 3: <meta charset> or http-equiv equivalent in <head>."""
    head = doc.find(".//head")
    if head is None:
        return [], 0.0  # Already flagged by check 2

    has_charset = False
    for meta in head.findall(".//meta"):
        if meta.get("charset"):
            has_charset = True
            break
        if (
            meta.get("http-equiv", "").lower() == "content-type"
            and "charset" in (meta.get("content", "")).lower()
        ):
            has_charset = True
            break

    if not has_charset:
        return ["Missing <meta charset> in <head>"], float(_param(config, "deduction_charset"))
    return [], 0.0


def check_viewport(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 4: <meta name='viewport'> in <head>."""
    head = doc.find(".//head")
    if head is None:
        return [], 0.0

    has_viewport = any(
        meta.get("name", "").lower() == "viewport" for meta in head.findall(".//meta")
    )
    if not has_viewport:
        return ['Missing <meta name="viewport"> in <head>'], float(
            _param(config, "deduction_viewport")
        )
    return [], 0.0


def check_title(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 5: <title> in <head>, non-empty."""
    head = doc.find(".//head")
    if head is None:
        return [], 0.0

    title = head.find(".//title")
    if title is None or not (title.text or "").strip():
        return ["Missing or empty <title> in <head>"], float(_param(config, "deduction_title"))
    return [], 0.0


def unclosed_tags(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 6: Unclosed block-level tags."""
    deduction = float(_param(config, "deduction_unclosed_tag"))
    max_reported = int(_param(config, "max_unclosed_tags_reported"))

    check_tags = ["div", "table", "tr", "td", "th", "p", "section", "header", "footer"]
    unclosed: list[str] = []

    for tag in check_tags:
        opens, closes = _count_raw_tags(raw_html, tag)
        if opens > closes:
            unclosed.append(f"<{tag}> ({opens} opened, {closes} closed)")

    issues: list[str] = []
    total = 0.0
    for item in unclosed[:max_reported]:
        issues.append(f"Unclosed tag: {item}")
        total += deduction

    if len(unclosed) > max_reported:
        issues.append(f"... and {len(unclosed) - max_reported} more unclosed tags")

    return issues, total


def block_in_inline(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 7: Block-in-inline nesting violations."""
    deduction = float(_param(config, "deduction_nesting"))
    max_reported = int(_param(config, "max_nesting_violations_reported"))

    violations: list[str] = []

    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue
        tag = el.tag.lower()
        if tag not in _BLOCK_TAGS:
            continue
        parent = el.getparent()
        while parent is not None:
            if not isinstance(parent.tag, str):
                break
            parent_tag = parent.tag.lower()
            if parent_tag in _INLINE_TAGS:
                violations.append(f"<{tag}> inside <{parent_tag}>")
                break
            if parent_tag in _BLOCK_TAGS or parent_tag in ("html", "head", "body"):
                break
            parent = parent.getparent()

    issues: list[str] = []
    total = 0.0
    for item in violations[:max_reported]:
        issues.append(f"Invalid nesting: {item}")
        total += deduction

    if len(violations) > max_reported:
        issues.append(f"... and {len(violations) - max_reported} more nesting violations")

    return issues, total


def duplicate_ids(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 8: Duplicate id attributes."""
    deduction = float(_param(config, "deduction_duplicate_id"))
    max_reported = int(_param(config, "max_duplicate_ids_reported"))

    id_counts: Counter[str] = Counter()
    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue
        el_id = el.get("id")
        if el_id:
            id_counts[el_id] += 1

    duplicates = [f'id="{k}" ({v} times)' for k, v in id_counts.items() if v > 1]

    issues: list[str] = []
    total = 0.0
    for item in duplicates[:max_reported]:
        issues.append(f"Duplicate {item}")
        total += deduction

    if len(duplicates) > max_reported:
        issues.append(f"... and {len(duplicates) - max_reported} more duplicate IDs")

    return issues, total


def empty_sections(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 9: Empty <head> or <body>."""
    deduction = float(_param(config, "deduction_empty_section"))
    issues: list[str] = []
    total = 0.0

    head = doc.find(".//head")
    if head is not None and len(head) == 0 and not (head.text or "").strip():
        issues.append("Empty <head> section")
        total += deduction

    body = doc.find(".//body")
    if body is not None and len(body) == 0 and not (body.text or "").strip():
        issues.append("Empty <body> section")
        total += deduction

    return issues, total


def style_placement(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 10: <style> must be in <head>; no <link rel='stylesheet'>."""
    deduction = float(_param(config, "deduction_style_placement"))
    issues: list[str] = []
    total = 0.0

    body = doc.find(".//body")
    if body is not None:
        body_styles = body.findall(".//style")
        if body_styles:
            issues.append(f"<style> in <body> ({len(body_styles)} found) — move to <head>")
            total += deduction

    for link in doc.findall(".//link"):
        if (link.get("rel") or "").lower() == "stylesheet":
            issues.append('<link rel="stylesheet"> found — external CSS not supported in email')
            total += deduction
            break

    return issues, total


def table_structure(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 11: Table hierarchy integrity."""
    deduction = float(_param(config, "deduction_table_structure"))
    max_reported = int(_param(config, "max_table_violations_reported"))

    violations: list[str] = []

    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue
        tag = el.tag.lower()

        if tag not in _TABLE_VALID_PARENTS:
            continue

        parent = el.getparent()
        if parent is None:
            continue
        if not isinstance(parent.tag, str):
            continue
        parent_tag = parent.tag.lower()

        valid_parents = _TABLE_VALID_PARENTS[tag]
        if parent_tag not in valid_parents:
            violations.append(
                f"<{tag}> inside <{parent_tag}> — must be inside "
                f"<{'> or <'.join(sorted(valid_parents))}>"
            )

    issues: list[str] = []
    total = 0.0
    for item in violations[:max_reported]:
        issues.append(f"Table structure: {item}")
        total += deduction

    if len(violations) > max_reported:
        issues.append(f"... and {len(violations) - max_reported} more table structure violations")

    return issues, total


def list_structure(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 12: List hierarchy — <li> must be inside <ul>/<ol>."""
    deduction = float(_param(config, "deduction_list_structure"))
    max_reported = int(_param(config, "max_list_violations_reported"))

    violations: list[str] = []

    for li in doc.iter("li"):
        parent = li.getparent()
        if parent is None:
            continue
        if not isinstance(parent.tag, str):
            continue
        if parent.tag.lower() not in ("ul", "ol"):
            violations.append(f"<li> inside <{parent.tag.lower()}> — must be inside <ul> or <ol>")

    issues: list[str] = []
    total = 0.0
    for item in violations[:max_reported]:
        issues.append(f"List structure: {item}")
        total += deduction

    if len(violations) > max_reported:
        issues.append(f"... and {len(violations) - max_reported} more list structure violations")

    return issues, total


def duplicate_structural_tags(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 13: Multiple <head>, <body>, or <title> tags."""
    deduction = float(_param(config, "deduction_duplicate_structural"))
    issues: list[str] = []
    total = 0.0

    for tag in ("head", "body", "title"):
        opens, _ = _count_raw_tags(raw_html, tag)
        if opens > 1:
            issues.append(f"Duplicate <{tag}> tags ({opens} found)")
            total += deduction

    return issues, total


def nested_links(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 14: <a> inside <a> — illegal per HTML spec."""
    deduction = float(_param(config, "deduction_nested_link"))

    depth = 0
    found_nested = False
    for match in re.finditer(r"<(/?)a[\s>]", raw_html, re.IGNORECASE):
        if match.group(1) == "":
            depth += 1
            if depth > 1:
                found_nested = True
                break
        else:
            depth = max(0, depth - 1)

    if found_nested:
        return ["Nested <a> tag inside <a> — illegal per HTML spec"], deduction
    return [], 0.0


def video_structure(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 15: <video> must have poster and fallback content."""
    deduction = float(_param(config, "deduction_missing_fallback"))
    issues: list[str] = []
    total = 0.0

    for video in doc.iter("video"):
        if not video.get("poster"):
            issues.append("<video> missing poster attribute (fallback image)")
            total += deduction
        has_fallback = bool((video.text or "").strip())
        if not has_fallback:
            for child in video:
                if isinstance(child.tag, str) and child.tag.lower() != "source":
                    has_fallback = True
                    break
                if (child.tail or "").strip():
                    has_fallback = True
                    break
        if not has_fallback:
            issues.append("<video> missing fallback content for non-supporting clients")
            total += deduction
        for source in video.findall("source"):
            if not source.get("type"):
                issues.append("<video> <source> missing type attribute")
                total += deduction
                break

    return issues, total


def audio_structure(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 16: <audio> must have fallback content."""
    deduction = float(_param(config, "deduction_missing_fallback"))
    issues: list[str] = []
    total = 0.0

    for audio in doc.iter("audio"):
        has_fallback = bool((audio.text or "").strip())
        if not has_fallback:
            for child in audio:
                if isinstance(child.tag, str) and child.tag.lower() != "source":
                    has_fallback = True
                    break
                if (child.tail or "").strip():
                    has_fallback = True
                    break
        if not has_fallback:
            issues.append("<audio> missing fallback content for non-supporting clients")
            total += deduction
        for source in audio.findall("source"):
            if not source.get("type"):
                issues.append("<audio> <source> missing type attribute")
                total += deduction
                break

    return issues, total


def picture_structure(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 17: <picture> must contain <img> fallback."""
    deduction = float(_param(config, "deduction_missing_fallback"))
    issues: list[str] = []
    total = 0.0

    for picture in doc.iter("picture"):
        img_children = picture.findall(".//img")
        if not img_children:
            issues.append("<picture> missing <img> fallback element")
            total += deduction

        for source in picture.findall("source"):
            if not source.get("srcset"):
                issues.append("<picture> <source> missing srcset attribute")
                total += deduction
                break
            if not source.get("type") and not source.get("media"):
                issues.append("<picture> <source> should have type or media attribute")
                total += deduction
                break

    return issues, total


def interactive_elements(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 18: Interactive & structured data elements."""
    deduction = float(_param(config, "deduction_interactive_structure"))
    issues: list[str] = []
    total = 0.0

    # Details/Summary
    for details in doc.iter("details"):
        children = [c for c in details if isinstance(c.tag, str)]
        if not children or children[0].tag.lower() != "summary":
            issues.append("<details> must have <summary> as first child")
            total += deduction

    # Input + Label pairing
    label_fors: set[str] = set()
    for label in doc.iter("label"):
        for_val = label.get("for")
        if for_val:
            label_fors.add(for_val)

    for inp in doc.iter("input"):
        inp_type = (inp.get("type") or "").lower()
        if inp_type in ("checkbox", "radio"):
            inp_id = inp.get("id")
            if not inp_id or inp_id not in label_fors:
                issues.append(
                    f'<input type="{inp_type}"> missing matching '
                    f'<label for="..."> (kinetic email pattern)'
                )
                total += deduction

    # JSON-LD validation
    for script in doc.iter("script"):
        script_type = (script.get("type") or "").lower()
        if script_type == "application/ld+json":
            content = (script.text or "").strip()
            if not content:
                issues.append('<script type="application/ld+json"> is empty')
                total += deduction
            else:
                try:
                    json.loads(content)
                except (json.JSONDecodeError, ValueError):
                    issues.append('<script type="application/ld+json"> contains invalid JSON')
                    total += deduction

    # Inline SVG
    svg_pattern = re.compile(r"<svg[\s>]", re.IGNORECASE)
    if svg_pattern.search(raw_html):
        for el in doc.iter():
            if not isinstance(el.tag, str):
                continue
            local_tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
            if local_tag.lower() == "svg":
                has_role = el.get("role") == "img"
                has_label = bool(el.get("aria-label"))
                if not has_role or not has_label:
                    issues.append(
                        'Inline <svg> should have role="img" and aria-label for accessibility'
                    )
                    total += deduction

    return issues, total


def template_element(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 19: <template> element — actively suppresses rendering."""
    deduction = float(_param(config, "deduction_dangerous_element"))

    if re.search(r"<template[\s>]", raw_html, re.IGNORECASE):
        return [
            "<template> element found — content is inert and will not render in email. "
            "Remove and use regular HTML elements instead"
        ], deduction
    return [], 0.0


def base_tag(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check 20: <base> tag — breaks all relative URLs in email."""
    deduction = float(_param(config, "deduction_dangerous_element"))

    base_tags = doc.findall(".//base")
    if base_tags:
        href = base_tags[0].get("href", "")
        return [
            f'<base href="{href}"> found — breaks all relative URLs, '
            f"tracking links, and image paths in email. Remove it"
        ], deduction
    return [], 0.0


# ---------------------------------------------------------------------------
# Register all custom check functions
# ---------------------------------------------------------------------------

register_custom_check("check_html_structure", check_html_structure)
register_custom_check("check_charset", check_charset)
register_custom_check("check_viewport", check_viewport)
register_custom_check("check_title", check_title)
register_custom_check("unclosed_tags", unclosed_tags)
register_custom_check("block_in_inline", block_in_inline)
register_custom_check("duplicate_ids", duplicate_ids)
register_custom_check("empty_sections", empty_sections)
register_custom_check("style_placement", style_placement)
register_custom_check("table_structure", table_structure)
register_custom_check("list_structure", list_structure)
register_custom_check("duplicate_structural_tags", duplicate_structural_tags)
register_custom_check("nested_links", nested_links)
register_custom_check("video_structure", video_structure)
register_custom_check("audio_structure", audio_structure)
register_custom_check("picture_structure", picture_structure)
register_custom_check("interactive_elements", interactive_elements)
register_custom_check("template_element", template_element)
register_custom_check("base_tag", base_tag)


# ---------------------------------------------------------------------------
# Custom check functions — accessibility (WCAG AA)
# ---------------------------------------------------------------------------

_A11Y_DEFAULTS: dict[str, float | int] = {
    "deduction_table_no_role": 0.10,
    "deduction_table_mixed_signals": 0.10,
    "deduction_data_table_no_headers": 0.10,
    "deduction_img_no_alt": 0.10,
    "deduction_tracking_pixel_alt": 0.05,
    "deduction_linked_img_no_alt": 0.10,
    "deduction_no_headings": 0.10,
    "deduction_skipped_heading": 0.10,
    "deduction_generic_link_text": 0.08,
    "deduction_empty_link": 0.10,
    "deduction_redundant_links": 0.05,
    "deduction_non_semantic_emphasis": 0.05,
    "deduction_preview_padding_no_aria": 0.08,
    "deduction_spacer_no_aria": 0.05,
    "deduction_separator_no_aria": 0.05,
    "deduction_outline_removed": 0.10,
    "deduction_br_spacing": 0.05,
    "deduction_dark_unsafe_colors": 0.08,
    "deduction_dark_no_overrides": 0.10,
    "deduction_input_no_label": 0.10,
    "deduction_required_no_aria": 0.08,
    "max_table_issues_reported": 5,
    "max_img_issues_reported": 5,
    "max_heading_issues_reported": 5,
    "max_link_issues_reported": 5,
    "max_content_issues_reported": 5,
    "max_form_issues_reported": 5,
}

_HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")

_GENERIC_LINK_TEXT = frozenset(
    {
        "click here",
        "here",
        "read more",
        "learn more",
        "more",
        "this",
        "link",
        "go",
        "see more",
        "find out more",
        "details",
        "info",
    }
)

_DATA_TABLE_SIGNALS = frozenset({"th", "caption", "thead", "tbody", "tfoot"})

_SEPARATOR_CHARS = frozenset({"|", "\u2022", "\u00b7", "\u2013", "\u2014"})


def _a11y_param(config: QACheckConfig | None, key: str) -> float | int:
    if config:
        val: float | int = config.params.get(key, _A11Y_DEFAULTS[key])
        return val
    return _A11Y_DEFAULTS[key]


def _is_tracking_pixel(img: HtmlElement) -> bool:
    """Detect tracking pixel / spacer images."""
    w = img.get("width", "")
    h = img.get("height", "")
    style = (img.get("style") or "").lower()

    # 1x1 or 0x0 via attributes
    if w in ("0", "1") and h in ("0", "1"):
        return True
    # Via inline style
    if "width:1px" in style.replace(" ", "") and "height:1px" in style.replace(" ", ""):
        return True
    if "width:0" in style.replace(" ", "") or "height:0" in style.replace(" ", ""):
        return True
    if "display:none" in style.replace(" ", ""):
        return True
    if "visibility:hidden" in style.replace(" ", ""):
        return True
    return False


def _has_data_table_signals(table: HtmlElement) -> bool:
    """Check if a table has data-table signals."""
    role = (table.get("role") or "").lower()
    if role in ("table", "grid"):
        return True
    if table.get("summary") is not None:
        return True
    for child in table.iter():
        if isinstance(child.tag, str) and child.tag.lower() in _DATA_TABLE_SIGNALS:
            return True
    return False


# --- B3: Layout table role detection ---


def layout_table_heuristic(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Layout tables without role='presentation'."""
    deduction = float(_a11y_param(config, "deduction_table_no_role"))
    cap = int(_a11y_param(config, "max_table_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for table in doc.iter("table"):
        role = (table.get("role") or "").lower()
        if role == "presentation":
            continue
        if _has_data_table_signals(table):
            continue
        # This is a layout table without role=presentation
        if len(issues) < cap:
            issues.append(
                "Layout table missing role='presentation' — "
                "screen readers announce table structure to users"
            )
        total += deduction

    return issues, total


# --- B4: Mixed signals on presentation tables ---


def table_mixed_signals(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Tables with role='presentation' that also have data-table signals."""
    deduction = float(_a11y_param(config, "deduction_table_mixed_signals"))
    cap = int(_a11y_param(config, "max_table_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for table in doc.iter("table"):
        role = (table.get("role") or "").lower()
        if role != "presentation":
            continue
        signals: list[str] = []
        if table.get("summary") is not None:
            signals.append("summary")
        for child in table.iter():
            if child is table:
                continue
            if isinstance(child.tag, str) and child.tag.lower() in ("th", "caption"):
                signals.append(f"<{child.tag.lower()}>")
        if signals:
            if len(issues) < cap:
                issues.append(
                    f"Table with role='presentation' has conflicting data-table signals: "
                    f"{', '.join(signals)}"
                )
            total += deduction

    return issues, total


# --- B5: Data table headers with scope ---


def data_table_headers(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Data tables: <th> must have scope='col' or scope='row'."""
    deduction = float(_a11y_param(config, "deduction_data_table_no_headers"))
    issues: list[str] = []
    total = 0.0

    for table in doc.iter("table"):
        role = (table.get("role") or "").lower()
        if role == "presentation":
            continue
        if not _has_data_table_signals(table):
            continue
        # This is a data table — check th elements
        for th in table.iter("th"):
            scope = (th.get("scope") or "").lower()
            if scope not in ("col", "row"):
                issues.append("Data table <th> missing scope='col' or scope='row'")
                total += deduction
                break  # One issue per table is enough

    return issues, total


# --- C6: Image alt attribute ---


def img_alt_present(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """All <img> must have alt attribute (alt='' is valid for decorative)."""
    deduction = float(_a11y_param(config, "deduction_img_no_alt"))
    cap = int(_a11y_param(config, "max_img_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for img in doc.iter("img"):
        if img.get("alt") is None:
            src = img.get("src", "")
            basename = src.rsplit("/", 1)[-1][:40] if src else "unknown"
            if len(issues) < cap:
                issues.append(f"<img> missing alt attribute (src: {basename})")
            total += deduction

    return issues, total


# --- C7: Tracking pixel alt ---


def tracking_pixel_alt(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Tracking pixels/spacers must have alt='' (empty, not missing, not descriptive)."""
    deduction = float(_a11y_param(config, "deduction_tracking_pixel_alt"))
    cap = int(_a11y_param(config, "max_img_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for img in doc.iter("img"):
        if not _is_tracking_pixel(img):
            continue
        alt = img.get("alt")
        if alt is None:
            if len(issues) < cap:
                issues.append("Tracking pixel missing alt='' — add empty alt attribute")
            total += deduction
        elif alt != "":
            if len(issues) < cap:
                issues.append(
                    f"Tracking pixel has descriptive alt=\"{alt[:30]}\" — should be alt='' (empty)"
                )
            total += deduction

    return issues, total


# --- C8: Linked image alt ---


def linked_img_alt(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """<a> containing only <img> — the img alt is the link's accessible name."""
    deduction = float(_a11y_param(config, "deduction_linked_img_no_alt"))
    cap = int(_a11y_param(config, "max_img_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for a_tag in doc.iter("a"):
        if not a_tag.get("href"):
            continue
        imgs = list(a_tag.iter("img"))
        if not imgs:
            continue
        # Check if <a> has text content besides the image
        text = (a_tag.text_content() or "").strip()
        # Remove img alt text from consideration
        img_alts = "".join((img.get("alt") or "") for img in imgs)
        remaining_text = text.replace(img_alts, "").strip() if img_alts else text
        if remaining_text:
            continue  # Text link alongside image — text provides accessible name

        # Only image(s) inside <a> — check alt
        for img in imgs:
            alt = img.get("alt")
            if alt is None or alt == "":
                if len(issues) < cap:
                    issues.append("Linked image with empty/missing alt — no accessible name")
                total += deduction
                break  # One issue per link

    return issues, total


# --- D9: Headings present ---


def headings_present(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Email body should contain heading elements for navigation."""
    deduction = float(_a11y_param(config, "deduction_no_headings"))
    body = doc.find(".//body")
    if body is None:
        return [], 0.0

    for tag in _HEADING_TAGS:
        if list(body.iter(tag)):
            return [], 0.0

    return [
        "No heading elements (h1-h6) found — screen reader users cannot navigate by heading"
    ], deduction


# --- D11: Heading hierarchy ---


def heading_hierarchy(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Heading levels must not skip (e.g., h1 -> h3 without h2)."""
    deduction = float(_a11y_param(config, "deduction_skipped_heading"))
    cap = int(_a11y_param(config, "max_heading_issues_reported"))
    issues: list[str] = []
    total = 0.0

    levels: list[int] = []
    body = doc.find(".//body")
    if body is None:
        return [], 0.0

    for el in body.iter():
        if isinstance(el.tag, str) and el.tag.lower() in _HEADING_TAGS:
            levels.append(int(el.tag[1]))

    for i in range(1, len(levels)):
        if levels[i] > levels[i - 1] + 1:
            if len(issues) < cap:
                issues.append(f"Skipped heading level: h{levels[i - 1]} → h{levels[i]}")
            total += deduction

    return issues, total


# --- E12: Generic link text ---


def generic_link_text(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Links should not use generic text like 'click here'."""
    deduction = float(_a11y_param(config, "deduction_generic_link_text"))
    cap = int(_a11y_param(config, "max_link_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for a_tag in doc.iter("a"):
        if not a_tag.get("href"):
            continue
        text = (a_tag.text_content() or "").strip().lower()
        if text in _GENERIC_LINK_TEXT:
            if len(issues) < cap:
                issues.append(f'Generic link text "{text}" — use descriptive text')
            total += deduction

    return issues, total


# --- E13: Empty links ---


def empty_links(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Links must have accessible name (text, aria-label, or img alt)."""
    deduction = float(_a11y_param(config, "deduction_empty_link"))
    cap = int(_a11y_param(config, "max_link_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for a_tag in doc.iter("a"):
        if not a_tag.get("href"):
            continue
        # Check for text content
        text = (a_tag.text_content() or "").strip()
        if text:
            continue
        # Check for aria-label
        if a_tag.get("aria-label"):
            continue
        # Check for img with non-empty alt
        has_img_alt = False
        for img in a_tag.iter("img"):
            alt = img.get("alt")
            if alt and alt.strip():
                has_img_alt = True
                break
        if has_img_alt:
            continue

        if len(issues) < cap:
            issues.append("Empty link — no text, aria-label, or image alt")
        total += deduction

    return issues, total


# --- E14: Redundant adjacent links ---


def redundant_links(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Consecutive <a> elements in same parent with same href."""
    deduction = float(_a11y_param(config, "deduction_redundant_links"))
    cap = int(_a11y_param(config, "max_link_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for parent in doc.iter():
        children = [c for c in parent if isinstance(c.tag, str) and c.tag.lower() == "a"]
        if len(children) < 2:
            continue
        for i in range(len(children) - 1):
            href1 = (children[i].get("href") or "").rstrip("/")
            href2 = (children[i + 1].get("href") or "").rstrip("/")
            if href1 and href1 == href2:
                if len(issues) < cap:
                    issues.append(
                        "Redundant adjacent links to same URL — "
                        "wrap image and text in a single <a>"
                    )
                total += deduction

    return issues, total


# --- F15: Semantic emphasis ---


def semantic_emphasis(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Use <strong>/<em> not <b>/<i> for emphasis."""
    deduction = float(_a11y_param(config, "deduction_non_semantic_emphasis"))

    b_count = len(list(doc.iter("b")))
    i_count = len(list(doc.iter("i")))
    total_count = b_count + i_count

    if total_count > 0:
        return [
            f"{total_count} <b>/<i> tag(s) found — use <strong>/<em> for semantic emphasis"
        ], deduction
    return [], 0.0


# --- F16: Preview padding aria-hidden ---


def preview_padding_aria(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Preview text padding (&zwnj;&nbsp; runs) must have aria-hidden='true'."""
    deduction = float(_a11y_param(config, "deduction_preview_padding_no_aria"))

    # Search for 3+ consecutive ZWNJ or NBSP characters
    padding_pattern = re.compile(r"[\u200c\u00a0]{3,}")

    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue
        # Check element text
        for text in [el.text, el.tail]:
            if text and padding_pattern.search(text):
                # Walk up to check if any ancestor has aria-hidden
                current: HtmlElement | None = el
                hidden = False
                while current is not None:
                    if isinstance(current.tag, str) and current.get("aria-hidden") == "true":
                        hidden = True
                        break
                    current = current.getparent()
                if not hidden:
                    return [
                        "Preview text padding (repeated \\u200c/\\u00a0) without aria-hidden='true'"
                    ], deduction

    return [], 0.0


# --- F17: Spacer cells/images aria-hidden ---


def spacer_aria(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Spacer cells (&nbsp; only) and spacer images without aria-hidden."""
    deduction = float(_a11y_param(config, "deduction_spacer_no_aria"))
    cap = int(_a11y_param(config, "max_content_issues_reported"))
    issues: list[str] = []
    total = 0.0

    # Spacer images
    for img in doc.iter("img"):
        src = (img.get("src") or "").lower()
        if "spacer" in src or "blank" in src:
            if img.get("aria-hidden") != "true":
                if len(issues) < cap:
                    issues.append("Spacer image without aria-hidden='true'")
                total += deduction

    return issues, total


# --- F18: Separator chars aria-hidden ---


def separator_aria(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Separator characters (|, bullet, dash) should have aria-hidden."""
    deduction = float(_a11y_param(config, "deduction_separator_no_aria"))
    cap = int(_a11y_param(config, "max_content_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue
        if el.tag.lower() in ("style", "script", "head"):
            continue
        text = (el.text_content() or "").strip()
        if len(text) <= 2 and text and text in _SEPARATOR_CHARS:
            if el.get("aria-hidden") != "true":
                if len(issues) < cap:
                    issues.append(f"Separator character '{text}' without aria-hidden='true'")
                total += deduction

    return issues, total


# --- F19: Outline removal ---


def outline_removal(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """outline:none/outline:0 found without replacement focus style."""
    deduction = float(_a11y_param(config, "deduction_outline_removed"))

    outline_pattern = re.compile(r"outline\s*:\s*(none|0)\b")

    # Check <style> blocks
    for style in doc.iter("style"):
        if style.text and outline_pattern.search(style.text):
            return [
                "outline:none/outline:0 found in styles — "
                "removes visible focus indicator for keyboard users"
            ], deduction

    # Check inline styles
    for el in doc.iter():
        if isinstance(el.tag, str):
            inline = el.get("style") or ""
            if outline_pattern.search(inline):
                return [
                    "outline:none/outline:0 found in inline style — removes visible focus indicator"
                ], deduction

    return [], 0.0


# --- F20: Consecutive <br> ---


def consecutive_br(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Consecutive <br> tags used for spacing instead of block elements."""
    deduction = float(_a11y_param(config, "deduction_br_spacing"))
    issues: list[str] = []
    total = 0.0

    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue
        children = list(el)
        for i, child in enumerate(children):
            if not isinstance(child.tag, str):
                continue
            if child.tag.lower() == "br" and i + 1 < len(children):
                tail = (child.tail or "").strip()
                next_child = children[i + 1]
                if not tail and isinstance(next_child.tag, str) and next_child.tag.lower() == "br":
                    issues.append("Consecutive <br> for spacing — use <p> or table cell padding")
                    total += deduction
                    return issues, total  # Single issue is enough

    return issues, total


# --- G21: Dark mode unsafe colors ---


def dark_unsafe_colors(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Dark mode styles using pure #ffffff/#000000 pairs."""
    deduction = float(_a11y_param(config, "deduction_dark_unsafe_colors"))

    # Collect all <style> text
    css_texts: list[str] = []
    for style in doc.iter("style"):
        if style.text:
            css_texts.append(style.text)
    combined = "\n".join(css_texts)

    # Find @media (prefers-color-scheme: dark) blocks
    dark_blocks = re.findall(
        r"@media\s*\([^)]*prefers-color-scheme\s*:\s*dark[^)]*\)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}",
        combined,
        re.IGNORECASE,
    )
    if not dark_blocks:
        return [], 0.0

    dark_css = " ".join(dark_blocks).lower()

    # Check for pure black/white pairs
    pure_white = re.search(
        r"(?:color|background(?:-color)?)\s*:\s*(?:#fff(?:fff)?|white)\b", dark_css
    )
    pure_black = re.search(
        r"(?:color|background(?:-color)?)\s*:\s*(?:#000(?:000)?|black)\b", dark_css
    )

    if pure_white and pure_black:
        return [
            "Dark mode uses pure #ffffff/#000000 — "
            "these invert unpredictably; use #f0f0f0 on #1a1a1a instead"
        ], deduction

    return [], 0.0


# --- G22: Dark mode meta without matching styles ---


def dark_no_overrides(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """color-scheme meta present but no @media (prefers-color-scheme: dark) styles."""
    deduction = float(_a11y_param(config, "deduction_dark_no_overrides"))

    # Check for dark mode meta tag
    has_meta = False
    for meta in doc.iter("meta"):
        name = (meta.get("name") or "").lower()
        content = (meta.get("content") or "").lower()
        if name == "color-scheme" and "dark" in content:
            has_meta = True
            break
        if name == "supported-color-schemes" and "dark" in content:
            has_meta = True
            break

    if not has_meta:
        return [], 0.0  # No dark mode declared — no issue

    # Check for matching dark mode styles
    css_texts: list[str] = []
    for style in doc.iter("style"):
        if style.text:
            css_texts.append(style.text)
    combined = "\n".join(css_texts)

    if not re.search(r"prefers-color-scheme\s*:\s*dark", combined, re.IGNORECASE):
        return [
            "color-scheme meta declares dark mode but no @media (prefers-color-scheme: dark) styles — "
            "clients will force-invert unpredictably"
        ], deduction

    # Check if dark mode block has color overrides
    dark_blocks = re.findall(
        r"@media\s*\([^)]*prefers-color-scheme\s*:\s*dark[^)]*\)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}",
        combined,
        re.IGNORECASE,
    )
    dark_css = " ".join(dark_blocks).lower()
    if not re.search(r"(?:color|background)", dark_css):
        return [
            "Dark mode @media block has no color overrides — "
            "add explicit color and background-color rules"
        ], deduction

    return [], 0.0


# --- H23: Form input labels ---


def input_label(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Form inputs must have associated <label>, aria-label, or aria-labelledby."""
    deduction = float(_a11y_param(config, "deduction_input_no_label"))
    cap = int(_a11y_param(config, "max_form_issues_reported"))
    issues: list[str] = []
    total = 0.0

    # Collect label[for] references
    label_fors: set[str] = set()
    for label in doc.iter("label"):
        for_val = label.get("for")
        if for_val:
            label_fors.add(for_val)

    skip_types = frozenset({"hidden", "submit", "button", "image", "reset"})

    for tag_name in ("input", "select", "textarea"):
        for el in doc.iter(tag_name):
            if tag_name == "input":
                inp_type = (el.get("type") or "text").lower()
                if inp_type in skip_types:
                    continue

            # Check for label association
            el_id = el.get("id")
            if el_id and el_id in label_fors:
                continue
            # Check if nested inside <label>
            parent: HtmlElement | None = el.getparent()
            nested_in_label = False
            while parent is not None:
                if isinstance(parent.tag, str) and parent.tag.lower() == "label":
                    nested_in_label = True
                    break
                parent = parent.getparent()
            if nested_in_label:
                continue
            # Check for aria-label or aria-labelledby
            if el.get("aria-label") or el.get("aria-labelledby"):
                continue

            has_placeholder = bool(el.get("placeholder"))
            if len(issues) < cap:
                if has_placeholder:
                    issues.append(
                        f"<{tag_name}> has only placeholder — not a substitute for <label>"
                    )
                else:
                    issues.append(f"<{tag_name}> missing associated <label> or aria-label")
            total += deduction

    return issues, total


# --- H24: Required fields aria-required ---


def required_aria(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Required fields must have aria-required='true'."""
    deduction = float(_a11y_param(config, "deduction_required_no_aria"))
    cap = int(_a11y_param(config, "max_form_issues_reported"))
    issues: list[str] = []
    total = 0.0

    for tag_name in ("input", "select", "textarea"):
        for el in doc.iter(tag_name):
            if el.get("required") is not None:
                if el.get("aria-required") != "true":
                    if len(issues) < cap:
                        issues.append(f"Required <{tag_name}> missing aria-required='true'")
                    total += deduction

    return issues, total


# Register all accessibility custom checks
register_custom_check("layout_table_heuristic", layout_table_heuristic)
register_custom_check("table_mixed_signals", table_mixed_signals)
register_custom_check("data_table_headers", data_table_headers)
register_custom_check("img_alt_present", img_alt_present)
register_custom_check("tracking_pixel_alt", tracking_pixel_alt)
register_custom_check("linked_img_alt", linked_img_alt)
register_custom_check("headings_present", headings_present)
register_custom_check("heading_hierarchy", heading_hierarchy)
register_custom_check("generic_link_text", generic_link_text)
register_custom_check("empty_links", empty_links)
register_custom_check("redundant_links", redundant_links)
register_custom_check("semantic_emphasis", semantic_emphasis)
register_custom_check("preview_padding_aria", preview_padding_aria)
register_custom_check("spacer_aria", spacer_aria)
register_custom_check("separator_aria", separator_aria)
register_custom_check("outline_removal", outline_removal)
register_custom_check("consecutive_br", consecutive_br)
register_custom_check("dark_unsafe_colors", dark_unsafe_colors)
register_custom_check("dark_no_overrides", dark_no_overrides)
register_custom_check("input_label", input_label)
register_custom_check("required_aria", required_aria)
