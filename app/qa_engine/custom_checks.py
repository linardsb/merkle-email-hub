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
from pathlib import Path
from typing import Any

from lxml.html import HtmlElement

from app.qa_engine.brand_analyzer import analyze_brand
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.dark_mode_parser import (
    _COLOR_PROPERTIES as _DM_COLOR_PROPERTIES,
)
from app.qa_engine.dark_mode_parser import (
    _hex_to_luminance,
    _parse_css_color,
    get_cached_dm_result,
)
from app.qa_engine.file_size_analyzer import get_cached_result as get_fs_cached_result
from app.qa_engine.link_parser import get_cached_link_result
from app.qa_engine.mso_parser import get_cached_result
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
        if not children or str(children[0].tag).lower() != "summary":
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
    return "visibility:hidden" in style.replace(" ", "")


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
                        "Redundant adjacent links to same URL — wrap image and text in a single <a>"
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
        if ("spacer" in src or "blank" in src) and img.get("aria-hidden") != "true":
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
        if len(text) <= 2 and text and text in _SEPARATOR_CHARS and el.get("aria-hidden") != "true":
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
            if el.get("required") is not None and el.get("aria-required") != "true":
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


# ─── MSO Fallback Custom Checks ─── (delegates to mso_parser module)


def _mso_param(config: QACheckConfig | None, key: str, default: float = 0.0) -> float:
    """Resolve an MSO check parameter from config or default."""
    if config:
        return float(config.params.get(key, default))
    return default


def mso_balanced_pairs(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check MSO conditional opener/closer balance."""
    result = get_cached_result(raw_html)
    issues = [i.message for i in result.issues if i.category == "balanced_pair"]
    deduction = _mso_param(config, "deduction_unbalanced_pair", 0.25) * len(issues)
    return issues, deduction


def mso_conditional_syntax(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check MSO conditional expression syntax validity."""
    result = get_cached_result(raw_html)
    issues = [i.message for i in result.issues if i.category == "syntax"]
    deduction = _mso_param(config, "deduction_invalid_syntax", 0.15) * len(issues)
    return issues, deduction


def mso_vml_nesting(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check VML elements are inside MSO conditional blocks."""
    result = get_cached_result(raw_html)
    issues = [i.message for i in result.issues if i.category == "vml_orphan"]
    deduction = _mso_param(config, "deduction_vml_orphan", 0.20) * len(issues)
    return issues, deduction


def mso_namespace_validation(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check VML/Office namespace declarations when VML elements are present."""
    result = get_cached_result(raw_html)
    issues = [i.message for i in result.issues if i.category == "namespace"]
    deduction = _mso_param(config, "deduction_missing_namespace", 0.15) * len(issues)
    return issues, deduction


def mso_ghost_table_validation(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check ghost table structure in MSO conditional blocks."""
    result = get_cached_result(raw_html)
    issues = [i.message for i in result.issues if i.category == "ghost_table"]
    deduction = _mso_param(config, "deduction_ghost_table_issue", 0.10) * len(issues)
    return issues, deduction


def mso_conditionals_present(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check that MSO conditional comments exist."""
    result = get_cached_result(raw_html)
    if result.opener_count == 0:
        deduction = _mso_param(config, "deduction_no_mso", 0.30)
        return ["No MSO conditional comments for Outlook fallbacks"], deduction
    return [], 0.0


def mso_namespaces_present(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check that VML/Office namespace declarations exist."""
    result = get_cached_result(raw_html)
    if not result.has_vml_namespace and not result.has_office_namespace:
        deduction = _mso_param(config, "deduction_no_namespaces", 0.20)
        return ["No VML/Office namespace declarations"], deduction
    return [], 0.0


register_custom_check("mso_balanced_pairs", mso_balanced_pairs)
register_custom_check("mso_conditional_syntax", mso_conditional_syntax)
register_custom_check("mso_vml_nesting", mso_vml_nesting)
register_custom_check("mso_namespace_validation", mso_namespace_validation)
register_custom_check("mso_ghost_table_validation", mso_ghost_table_validation)
register_custom_check("mso_conditionals_present", mso_conditionals_present)
register_custom_check("mso_namespaces_present", mso_namespaces_present)


# ─── Dark Mode Semantic Checks ─── (delegates to dark_mode_parser module)


def _dm_param(config: QACheckConfig | None, key: str, default: float = 0.0) -> float:
    """Resolve a dark mode check parameter from config or default."""
    if config:
        return float(config.params.get(key, default))
    return default


def dm_color_scheme_meta(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check color-scheme meta tag is present, valid, and includes 'dark'."""
    deduction = float(_dm_param(config, "deduction_missing_color_scheme", 0.15))
    result = get_cached_dm_result(raw_html)
    if not result.meta_tags.has_color_scheme:
        return (["Missing <meta name='color-scheme' content='light dark'>"], deduction)
    if "dark" not in result.meta_tags.content_value.lower():
        return (["color-scheme meta present but content doesn't include 'dark'"], deduction)
    return ([], 0.0)


def dm_supported_color_schemes(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check supported-color-schemes companion meta tag."""
    deduction = float(_dm_param(config, "deduction_missing_supported", 0.05))
    result = get_cached_dm_result(raw_html)
    if not result.meta_tags.has_supported_color_schemes:
        return (
            ["Missing <meta name='supported-color-schemes'> companion tag for older Apple Mail"],
            deduction,
        )
    return ([], 0.0)


def dm_css_color_scheme_property(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check CSS color-scheme property on :root or html."""
    deduction = float(_dm_param(config, "deduction_missing_css_color_scheme", 0.05))
    result = get_cached_dm_result(raw_html)
    if not result.meta_tags.has_css_color_scheme:
        return (
            ["Missing 'color-scheme: light dark' CSS property on :root"],
            deduction,
        )
    return ([], 0.0)


def dm_meta_placement(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check color-scheme meta tag is in <head> not <body>."""
    deduction = float(_dm_param(config, "deduction_meta_misplaced", 0.10))
    result = get_cached_dm_result(raw_html)
    # Only flag if meta exists AND is misplaced
    if result.meta_tags.has_color_scheme and not result.meta_tags.color_scheme_in_head:
        return (["color-scheme meta tag found in <body> instead of <head>"], deduction)
    return ([], 0.0)


def dm_media_query_present(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check @media (prefers-color-scheme: dark) block exists."""
    deduction = float(_dm_param(config, "deduction_no_media_query", 0.25))
    result = get_cached_dm_result(raw_html)
    if not result.media_queries:
        return (["No @media (prefers-color-scheme: dark) block found"], deduction)
    return ([], 0.0)


def dm_media_query_has_colors(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check dark mode media query contains color declarations."""
    deduction = float(_dm_param(config, "deduction_empty_media_query", 0.20))
    result = get_cached_dm_result(raw_html)
    if not result.media_queries:
        return ([], 0.0)  # No media query — handled by dm_media_query_present
    if not any(mq.has_color_props for mq in result.media_queries):
        return (
            ["prefers-color-scheme: dark block exists but contains no color properties"],
            deduction,
        )
    return ([], 0.0)


def dm_media_query_important(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check dark mode color declarations use !important."""
    deduction = float(_dm_param(config, "deduction_missing_important", 0.10))
    cap = int(_dm_param(config, "max_dm_issues_reported", 5))
    result = get_cached_dm_result(raw_html)
    issues: list[str] = []
    total = 0.0

    for mq in result.media_queries:
        for decl in mq.declarations:
            if decl.property in _DM_COLOR_PROPERTIES and not decl.has_important:
                if len(issues) < cap:
                    issues.append(f"Dark mode '{decl.property}: {decl.value}' missing !important")
                total += deduction

    return issues, total


def dm_ogsc_present(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check [data-ogsc] Outlook.com text color selectors exist."""
    deduction = float(_dm_param(config, "deduction_no_ogsc", 0.10))
    result = get_cached_dm_result(raw_html)
    if not any(s.selector_type == "ogsc" for s in result.outlook_selectors):
        return (["No [data-ogsc] selectors — Outlook.com will force-invert text colors"], deduction)
    return ([], 0.0)


def dm_ogsb_present(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check [data-ogsb] Outlook.com background selectors exist."""
    deduction = float(_dm_param(config, "deduction_no_ogsb", 0.10))
    result = get_cached_dm_result(raw_html)
    if not any(s.selector_type == "ogsb" for s in result.outlook_selectors):
        return (
            ["No [data-ogsb] selectors — Outlook.com will force-invert background colors"],
            deduction,
        )
    return ([], 0.0)


def dm_outlook_selectors_have_content(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check Outlook selectors contain actual CSS declarations."""
    deduction = float(_dm_param(config, "deduction_empty_outlook", 0.10))
    result = get_cached_dm_result(raw_html)
    if not result.outlook_selectors:
        return ([], 0.0)  # No selectors — handled by ogsc/ogsb presence checks
    empty = [s for s in result.outlook_selectors if not s.has_declarations]
    if empty:
        return (
            ["Outlook [data-ogsc]/[data-ogsb] selectors present but contain no CSS declarations"],
            deduction,
        )
    return ([], 0.0)


def dm_no_invisible_text(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check for near-identical foreground/background in dark mode color pairs."""
    deduction = float(_dm_param(config, "deduction_invisible_text", 0.20))
    cap = int(_dm_param(config, "max_dm_issues_reported", 3))
    result = get_cached_dm_result(raw_html)
    issues: list[str] = []
    total = 0.0

    for pair in result.color_pairs:
        if pair.contrast_ratio > 0 and pair.contrast_ratio < 1.5:
            if len(issues) < cap:
                issues.append(
                    f"Near-invisible text in dark mode: {pair.selector} "
                    f"{pair.css_property} contrast ratio {pair.contrast_ratio}:1"
                )
            total += deduction

    return issues, total


def dm_contrast_ratio(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check dark mode color pairs meet WCAG AA 4.5:1 contrast ratio."""
    deduction = float(_dm_param(config, "deduction_low_contrast", 0.10))
    cap = int(_dm_param(config, "max_dm_issues_reported", 5))
    result = get_cached_dm_result(raw_html)
    issues: list[str] = []
    total = 0.0

    for pair in result.color_pairs:
        if pair.contrast_ratio > 0 and pair.contrast_ratio < 4.5 and pair.contrast_ratio >= 1.5:
            if len(issues) < cap:
                issues.append(
                    f"Low contrast in dark mode: {pair.selector} "
                    f"{pair.css_property} ratio {pair.contrast_ratio}:1 (need 4.5:1)"
                )
            total += deduction

    return issues, total


def dm_backgrounds_are_dark(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check dark mode background colors have low luminance (are actually dark)."""
    deduction = float(_dm_param(config, "deduction_light_dark_bg", 0.10))
    cap = int(_dm_param(config, "max_dm_issues_reported", 3))
    result = get_cached_dm_result(raw_html)
    issues: list[str] = []
    total = 0.0

    for pair in result.color_pairs:
        if pair.css_property in {"background-color", "background"}:
            dark_hex = _parse_css_color(pair.dark_value)
            if dark_hex:
                luminance = _hex_to_luminance(dark_hex)
                if luminance > 0.4:
                    if len(issues) < cap:
                        issues.append(
                            f"Dark mode background {pair.dark_value} on {pair.selector} "
                            f"has high luminance ({luminance:.2f}) — should be dark"
                        )
                    total += deduction

    return issues, total


def dm_image_swap_alt(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check dark mode swap images have empty alt text."""
    deduction = float(_dm_param(config, "deduction_swap_img_alt", 0.05))
    cap = int(_dm_param(config, "max_dm_issues_reported", 3))
    issues: list[str] = []
    total = 0.0

    # Find images with dark-mode-related classes that are hidden by default
    for img in doc.iter("img"):
        classes = (img.get("class") or "").lower()
        style = (img.get("style") or "").lower()
        if any(c in classes for c in ("dark-img", "dark-image", "dark-logo", "dark_img")) and (
            "display: none" in style or "display:none" in style
        ):
            alt = img.get("alt")
            if alt is not None and alt != "" and len(issues) < cap:
                issues.append(
                    "Dark mode swap image should have alt='' to avoid "
                    "duplicate screen reader announcements"
                )
                total += deduction

    return issues, total


def dm_hidden_img_mso(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check hidden dark mode images include mso-hide:all for Outlook."""
    deduction = float(_dm_param(config, "deduction_no_mso_hide", 0.05))
    cap = int(_dm_param(config, "max_dm_issues_reported", 3))
    issues: list[str] = []
    total = 0.0

    for img in doc.iter("img"):
        classes = (img.get("class") or "").lower()
        style = img.get("style") or ""
        if (
            any(c in classes for c in ("dark-img", "dark-image", "dark-logo", "dark_img"))
            and ("display: none" in style.lower() or "display:none" in style.lower())
            and not re.search(r"mso-hide\s*:\s*all", style, re.IGNORECASE)
            and len(issues) < cap
        ):
            issues.append(
                "Dark mode swap image hidden by default should include 'mso-hide: all' for Outlook"
            )
            total += deduction

    return issues, total


def dm_any_support_present(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check that at least some dark mode support exists."""
    deduction = float(_dm_param(config, "deduction_no_dark_mode", 0.30))
    result = get_cached_dm_result(raw_html)
    has_meta = result.meta_tags.has_color_scheme
    has_media = len(result.media_queries) > 0
    has_outlook = len(result.outlook_selectors) > 0
    if not has_meta and not has_media and not has_outlook:
        return (
            [
                "No dark mode support detected — no meta tags, no media queries, no Outlook selectors"
            ],
            deduction,
        )
    return ([], 0.0)


register_custom_check("dm_color_scheme_meta", dm_color_scheme_meta)
register_custom_check("dm_supported_color_schemes", dm_supported_color_schemes)
register_custom_check("dm_css_color_scheme_property", dm_css_color_scheme_property)
register_custom_check("dm_meta_placement", dm_meta_placement)
register_custom_check("dm_media_query_present", dm_media_query_present)
register_custom_check("dm_media_query_has_colors", dm_media_query_has_colors)
register_custom_check("dm_media_query_important", dm_media_query_important)
register_custom_check("dm_ogsc_present", dm_ogsc_present)
register_custom_check("dm_ogsb_present", dm_ogsb_present)
register_custom_check("dm_outlook_selectors_have_content", dm_outlook_selectors_have_content)
register_custom_check("dm_no_invisible_text", dm_no_invisible_text)
register_custom_check("dm_contrast_ratio", dm_contrast_ratio)
register_custom_check("dm_backgrounds_are_dark", dm_backgrounds_are_dark)
register_custom_check("dm_image_swap_alt", dm_image_swap_alt)
register_custom_check("dm_hidden_img_mso", dm_hidden_img_mso)
register_custom_check("dm_any_support_present", dm_any_support_present)


# ─── Link Validation Custom Checks ─── (delegates to link_parser module)


def _link_param(config: QACheckConfig | None, key: str, default: float) -> float:
    """Resolve a link check parameter from config."""
    if config:
        return float(config.params.get(key, default))
    return default


def link_non_https(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag non-HTTPS links (except localhost)."""
    deduction = _link_param(config, "deduction_http_link", 0.10)
    cap = int(_link_param(config, "max_link_issues_reported", 5))
    result = get_cached_link_result(raw_html)
    matching = [i for i in result.issues if i.category == "non_https"]
    issues = [i.message for i in matching[:cap]]
    total = deduction * len(matching)
    return issues, total


def link_malformed_url(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag malformed URLs (missing scheme, netloc, path traversal)."""
    deduction = _link_param(config, "deduction_malformed_url", 0.15)
    cap = int(_link_param(config, "max_link_issues_reported", 5))
    result = get_cached_link_result(raw_html)
    matching = [i for i in result.issues if i.category == "malformed_url"]
    issues = [i.message for i in matching[:cap]]
    total = deduction * len(matching)
    return issues, total


def link_blocked_protocol(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag javascript:/data:/vbscript: protocols."""
    deduction = _link_param(config, "deduction_blocked_protocol", 0.25)
    cap = int(_link_param(config, "max_link_issues_reported", 3))
    result = get_cached_link_result(raw_html)
    matching = [i for i in result.issues if i.category == "suspicious_protocol"]
    issues = [i.message for i in matching[:cap]]
    total = deduction * len(matching)
    return issues, total


def link_empty_href(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag empty or fragment-only hrefs."""
    deduction = _link_param(config, "deduction_empty_href", 0.05)
    cap = int(_link_param(config, "max_link_issues_reported", 5))
    result = get_cached_link_result(raw_html)
    matching = [i for i in result.issues if i.category == "empty_href"]
    issues = [i.message for i in matching[:cap]]
    total = deduction * len(matching)
    return issues, total


def link_template_balanced(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag unbalanced ESP template variable delimiters in hrefs."""
    deduction = _link_param(config, "deduction_template_unbalanced", 0.15)
    cap = int(_link_param(config, "max_link_issues_reported", 5))
    result = get_cached_link_result(raw_html)
    matching = [i for i in result.issues if i.category == "template_syntax"]
    issues = [i.message for i in matching[:cap]]
    total = deduction * len(matching)
    return issues, total


def link_unencoded_chars(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag unencoded spaces or special characters in URLs."""
    deduction = _link_param(config, "deduction_unencoded", 0.05)
    cap = int(_link_param(config, "max_link_issues_reported", 3))
    result = get_cached_link_result(raw_html)
    matching = [i for i in result.issues if i.category == "unencoded_chars"]
    issues = [i.message for i in matching[:cap]]
    total = deduction * len(matching)
    return issues, total


def link_double_encoded(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag double-encoded URL characters (e.g. %2520)."""
    deduction = _link_param(config, "deduction_double_encoded", 0.05)
    cap = int(_link_param(config, "max_link_issues_reported", 3))
    result = get_cached_link_result(raw_html)
    matching = [i for i in result.issues if i.category == "double_encoded"]
    issues = [i.message for i in matching[:cap]]
    total = deduction * len(matching)
    return issues, total


def link_phishing_mismatch(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag links where display text URL domain differs from href domain."""
    deduction = _link_param(config, "deduction_phishing", 0.20)
    cap = int(_link_param(config, "max_link_issues_reported", 3))
    result = get_cached_link_result(raw_html)
    matching = [i for i in result.issues if i.category == "phishing_mismatch"]
    issues = [i.message for i in matching[:cap]]
    total = deduction * len(matching)
    return issues, total


def link_has_any(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Informational: report if zero links found."""
    result = get_cached_link_result(raw_html)
    if result.total_links == 0:
        return ["No links found in email"], 0.0
    return [], 0.0


def link_accessible_text(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check links have visible text or image alt text."""
    deduction = _link_param(config, "deduction_no_link_text", 0.05)
    cap = int(_link_param(config, "max_link_issues_reported", 5))
    result = get_cached_link_result(raw_html)
    issues: list[str] = []
    total = 0.0

    for link in result.links:
        if link.text:
            continue
        # link.text comes from lxml text_content() which includes descendant
        # img alt text — so empty text means no visible text AND no img alt
        if link.href:
            if len(issues) < cap:
                issues.append(f"Link has no accessible text: {link.href[:60]}")
            total += deduction

    return issues, total


def link_vml_href(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check VML elements with href attributes in MSO conditional blocks."""
    from app.qa_engine.link_parser import _VML_HREF_RE

    deduction = _link_param(config, "deduction_vml_href", 0.10)
    cap = int(_link_param(config, "max_link_issues_reported", 3))
    issues: list[str] = []
    total = 0.0

    for match in _VML_HREF_RE.finditer(raw_html):
        vml_href = match.group(1)
        if vml_href:
            if len(issues) < cap:
                issues.append(
                    f"VML href found: {vml_href[:60]} — ensure it matches "
                    f"the corresponding <a> href (ESPs only rewrite <a> tags)"
                )
            total += deduction

    return issues, total


register_custom_check("link_non_https", link_non_https)
register_custom_check("link_malformed_url", link_malformed_url)
register_custom_check("link_blocked_protocol", link_blocked_protocol)
register_custom_check("link_empty_href", link_empty_href)
register_custom_check("link_template_balanced", link_template_balanced)
register_custom_check("link_unencoded_chars", link_unencoded_chars)
register_custom_check("link_double_encoded", link_double_encoded)
register_custom_check("link_phishing_mismatch", link_phishing_mismatch)
register_custom_check("link_has_any", link_has_any)
register_custom_check("link_accessible_text", link_accessible_text)
register_custom_check("link_vml_href", link_vml_href)


# ─── File Size Custom Checks ─── (delegates to file_size_analyzer module)


def _fs_param(config: QACheckConfig | None, key: str, default: float) -> float:
    """Resolve file size config parameter."""
    if config and key in config.params:
        return float(config.params[key])
    return default


def file_size_gmail_threshold(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check HTML size against Gmail 102KB clipping threshold."""
    result = get_fs_cached_result(raw_html)
    threshold = _fs_param(config, "gmail_threshold_kb", 102.0)
    if result.raw_size_kb > threshold:
        deduction = _fs_param(config, "deduction_gmail_clip", 0.30)
        return [
            f"HTML is {result.raw_size_kb:.1f}KB — exceeds Gmail {threshold:.0f}KB clipping threshold"
        ], deduction
    return [], 0.0


def file_size_outlook_threshold(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check HTML size against Outlook 100KB performance threshold."""
    result = get_fs_cached_result(raw_html)
    threshold = _fs_param(config, "outlook_threshold_kb", 100.0)
    if result.raw_size_kb > threshold:
        deduction = _fs_param(config, "deduction_outlook_perf", 0.20)
        return [
            f"HTML is {result.raw_size_kb:.1f}KB — exceeds Outlook {threshold:.0f}KB performance threshold"
        ], deduction
    return [], 0.0


def file_size_yahoo_threshold(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check HTML size against Yahoo 75KB conservative threshold."""
    result = get_fs_cached_result(raw_html)
    threshold = _fs_param(config, "yahoo_threshold_kb", 75.0)
    if result.raw_size_kb > threshold:
        deduction = _fs_param(config, "deduction_yahoo_clip", 0.10)
        return [
            f"HTML is {result.raw_size_kb:.1f}KB — exceeds Yahoo {threshold:.0f}KB threshold"
        ], deduction
    return [], 0.0


def file_size_braze_limit(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check HTML size against Braze 100KB hard limit."""
    result = get_fs_cached_result(raw_html)
    threshold = _fs_param(config, "braze_threshold_kb", 100.0)
    if result.raw_size_kb > threshold:
        deduction = _fs_param(config, "deduction_braze_limit", 0.15)
        return [
            f"HTML is {result.raw_size_kb:.1f}KB — exceeds Braze {threshold:.0f}KB hard limit"
        ], deduction
    return [], 0.0


def file_size_inline_css_ratio(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check inline CSS does not exceed configured percentage of total size."""
    result = get_fs_cached_result(raw_html)
    max_pct = _fs_param(config, "inline_css_max_pct", 40.0)
    if result.breakdown.inline_styles_pct > max_pct:
        deduction = _fs_param(config, "deduction_inline_css_bloat", 0.05)
        return [
            f"Inline styles are {result.breakdown.inline_styles_pct:.0f}% of HTML "
            f"({result.breakdown.inline_styles_bytes / 1024:.1f}KB) — exceeds {max_pct:.0f}% threshold"
        ], deduction
    return [], 0.0


def file_size_mso_ratio(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check MSO conditional blocks do not exceed configured percentage."""
    result = get_fs_cached_result(raw_html)
    max_pct = _fs_param(config, "mso_conditional_max_pct", 25.0)
    if result.breakdown.mso_conditional_pct > max_pct:
        deduction = _fs_param(config, "deduction_mso_bloat", 0.05)
        return [
            f"MSO conditionals are {result.breakdown.mso_conditional_pct:.0f}% of HTML "
            f"({result.breakdown.mso_conditional_bytes / 1024:.1f}KB) — exceeds {max_pct:.0f}% threshold"
        ], deduction
    return [], 0.0


def file_size_gzip_efficiency(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check gzip compression achieves minimum reduction (skip tiny emails)."""
    result = get_fs_cached_result(raw_html)
    min_reduction = _fs_param(config, "gzip_min_reduction_pct", 50.0)
    reduction_pct = (1.0 - result.compression_ratio) * 100
    if reduction_pct < min_reduction and result.raw_size_kb > 20:
        deduction = _fs_param(config, "deduction_poor_gzip", 0.05)
        return [
            f"Gzip compression only reduces size by {reduction_pct:.0f}% "
            f"({result.raw_size_kb:.1f}KB → {result.gzip_size_kb:.1f}KB) — "
            f"may contain base64-encoded data or large inline assets"
        ], deduction
    return [], 0.0


def file_size_summary(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Informational summary — always 0 deduction."""
    result = get_fs_cached_result(raw_html)
    b = result.breakdown
    summary = (
        f"Raw: {result.raw_size_kb:.1f}KB | Gzip: {result.gzip_size_kb:.1f}KB "
        f"({(1 - result.compression_ratio) * 100:.0f}% reduction) | "
        f"Breakdown: styles {b.inline_styles_pct:.0f}%/{b.head_styles_pct:.0f}%, "
        f"MSO {b.mso_conditional_pct:.0f}%, "
        f"images {b.image_tag_bytes / max(b.total_bytes, 1) * 100:.0f}%"
    )
    return [summary], 0.0


register_custom_check("file_size_gmail_threshold", file_size_gmail_threshold)
register_custom_check("file_size_outlook_threshold", file_size_outlook_threshold)
register_custom_check("file_size_yahoo_threshold", file_size_yahoo_threshold)
register_custom_check("file_size_braze_limit", file_size_braze_limit)
register_custom_check("file_size_inline_css_ratio", file_size_inline_css_ratio)
register_custom_check("file_size_mso_ratio", file_size_mso_ratio)
register_custom_check("file_size_gzip_efficiency", file_size_gzip_efficiency)
register_custom_check("file_size_summary", file_size_summary)


# ---------------------------------------------------------------------------
# Spam Score — trigger phrases, formatting heuristics, obfuscation detection
# ---------------------------------------------------------------------------

_SPAM_TRIGGERS_PATH = Path(__file__).parent / "data" / "spam_triggers.yaml"

_spam_trigger_cache: list[dict[str, str | float]] | None = None


def _load_spam_triggers() -> list[dict[str, str | float]]:
    """Load and cache spam trigger phrases from YAML."""
    global _spam_trigger_cache
    if _spam_trigger_cache is not None:
        return _spam_trigger_cache

    import yaml

    if not _SPAM_TRIGGERS_PATH.exists():
        _spam_trigger_cache = []
        return _spam_trigger_cache

    with _SPAM_TRIGGERS_PATH.open() as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    triggers: list[dict[str, str | float]] = data.get("triggers", [])
    _spam_trigger_cache = triggers
    return _spam_trigger_cache


# Pre-compiled regex cache for trigger phrases
_trigger_patterns: dict[str, re.Pattern[str]] = {}


def _get_trigger_pattern(phrase: str) -> re.Pattern[str]:
    """Get pre-compiled word-boundary regex for a trigger phrase."""
    if phrase not in _trigger_patterns:
        _trigger_patterns[phrase] = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
    return _trigger_patterns[phrase]


def _extract_text(raw_html: str) -> str:
    """Strip HTML tags to get plain text for trigger matching."""
    return re.sub(r"<[^>]+>", " ", raw_html)


def spam_trigger_scan(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Scan email body text for known spam trigger phrases with weighted scoring."""
    triggers = _load_spam_triggers()
    text = _extract_text(raw_html)

    issues: list[str] = []
    total_deduction = 0.0
    max_reported: int = int(config.params.get("max_triggers_reported", 10) if config else 10)

    for trigger in triggers:
        phrase = str(trigger.get("phrase", ""))
        weight = float(trigger.get("weight", 0.10))
        category = str(trigger.get("category", "unknown"))
        pattern = _get_trigger_pattern(phrase)

        matches = pattern.findall(text)
        if matches:
            total_deduction += weight
            if len(issues) < max_reported:
                issues.append(f"'{phrase}' ({category}, -{weight:.2f})")

    return issues, total_deduction


def spam_subject_triggers(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check subject line (title tag) for spam triggers — 3x weight multiplier."""
    triggers = _load_spam_triggers()
    subject_multiplier = float(
        config.params.get("subject_weight_multiplier", 3.0) if config else 3.0
    )

    # Extract subject from <title> tag
    titles = list(doc.iter("title"))
    if not titles:
        return [], 0.0

    subject_text = (titles[0].text_content() or "").strip()
    if not subject_text:
        return [], 0.0

    issues: list[str] = []
    total_deduction = 0.0

    for trigger in triggers:
        phrase = str(trigger.get("phrase", ""))
        weight = float(trigger.get("weight", 0.10))
        category = str(trigger.get("category", "unknown"))
        pattern = _get_trigger_pattern(phrase)

        if pattern.search(subject_text):
            adjusted_weight = weight * subject_multiplier
            total_deduction += adjusted_weight
            issues.append(f"Subject: '{phrase}' ({category}, -{adjusted_weight:.2f})")

    return issues, total_deduction


# Formatting heuristic patterns (pre-compiled at module load)
_EXCESSIVE_PUNCTUATION = re.compile(r"[!?]{3,}")
_ALL_CAPS_WORD = re.compile(r"\b[A-Z]{2,}\b")
_OBFUSCATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b\w*\d+\w*\b"), "leet-speak"),  # words with digits mixed in
]
# Common leet-speak substitutions
_LEET_MAP: dict[str, str] = {
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "8": "b",
    "@": "a",
    "$": "s",
}
_LEET_DECODE = re.compile(r"[0134578@$]")
_KNOWN_LEET_WORDS = frozenset(
    {
        "free",
        "sale",
        "discount",
        "offer",
        "cash",
        "prize",
        "bonus",
        "credit",
        "viagra",
        "casino",
        "winner",
    }
)


def spam_excessive_punctuation(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect excessive punctuation (3+ consecutive ! or ?)."""
    text = _extract_text(raw_html)
    matches = _EXCESSIVE_PUNCTUATION.findall(text)
    deduction = float(
        config.params.get("deduction_excessive_punctuation", 0.10) if config else 0.10
    )

    if not matches:
        return [], 0.0

    issues = [f"Excessive punctuation: {len(matches)} instance(s) of 3+ consecutive !/?"]
    return issues, deduction


def spam_all_caps_words(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect sequences of 3+ all-caps words."""
    text = _extract_text(raw_html)
    words = text.split()
    deduction = float(config.params.get("deduction_all_caps", 0.10) if config else 0.10)

    # Find runs of consecutive all-caps words (2+ chars each)
    consecutive = 0
    max_run = 0
    for word in words:
        # Strip punctuation for check
        clean = re.sub(r"[^\w]", "", word)
        if len(clean) >= 2 and clean.isupper():
            consecutive += 1
            max_run = max(max_run, consecutive)
        else:
            consecutive = 0

    if max_run >= 3:
        return [f"All-caps sequence: {max_run} consecutive all-caps words"], deduction

    return [], 0.0


def spam_obfuscation(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect character obfuscation (leet-speak substitution)."""
    text = _extract_text(raw_html)
    deduction = float(config.params.get("deduction_obfuscation", 0.15) if config else 0.15)

    # Find words containing digit substitutions and decode them
    issues: list[str] = []
    # Match words that have a mix of letters and digits (potential leet-speak)
    leet_candidates = re.findall(r"\b[a-zA-Z0-9@$]{3,}\b", text)

    for candidate in leet_candidates:
        if not _LEET_DECODE.search(candidate):
            continue
        # Decode leet-speak
        decoded = ""
        for ch in candidate.lower():
            decoded += _LEET_MAP.get(ch) or ch
        if decoded in _KNOWN_LEET_WORDS and decoded != candidate.lower():
            issues.append(f"Obfuscated word: '{candidate}' (decoded: '{decoded}')")

    if issues:
        return issues[:5], deduction

    return [], 0.0


def spam_score_summary(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Informational summary — no deduction."""
    triggers = _load_spam_triggers()
    text = _extract_text(raw_html)

    matched_count = 0
    categories: Counter[str] = Counter()

    for trigger in triggers:
        phrase = str(trigger.get("phrase", ""))
        category = str(trigger.get("category", "unknown"))
        pattern = _get_trigger_pattern(phrase)
        if pattern.search(text):
            matched_count += 1
            categories[category] += 1

    if matched_count == 0:
        return [], 0.0

    cat_breakdown = ", ".join(f"{cat}: {count}" for cat, count in categories.most_common())
    return [f"Triggers matched: {matched_count}/{len(triggers)} ({cat_breakdown})"], 0.0


register_custom_check("spam_trigger_scan", spam_trigger_scan)
register_custom_check("spam_subject_triggers", spam_subject_triggers)
register_custom_check("spam_excessive_punctuation", spam_excessive_punctuation)
register_custom_check("spam_all_caps_words", spam_all_caps_words)
register_custom_check("spam_obfuscation", spam_obfuscation)
register_custom_check("spam_score_summary", spam_score_summary)


# ---------------------------------------------------------------------------
# Custom check functions — brand compliance
# ---------------------------------------------------------------------------

_GENERIC_FONTS = frozenset(
    {
        "serif",
        "sans-serif",
        "monospace",
        "cursive",
        "fantasy",
        "system-ui",
        "ui-serif",
        "ui-sans-serif",
        "ui-monospace",
    }
)


def _brand_param(config: QACheckConfig | None, key: str, default: float) -> float:
    """Resolve a brand compliance config parameter."""
    if config and key in config.params:
        return float(config.params[key])
    return default


def brand_color_compliance(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check CSS colors against allowed brand palette."""
    allowed_raw: list[str] = config.params.get("allowed_colors", []) if config else []
    if not allowed_raw:
        return [], 0.0

    allowed = {c.strip().lower() for c in allowed_raw}
    # Expand 3-char hex
    expanded: set[str] = set()
    for c in allowed:
        expanded.add(c)
        if re.match(r"^#[0-9a-f]{3}$", c):
            expanded.add(f"#{c[1] * 2}{c[2] * 2}{c[3] * 2}")
    allowed = expanded

    analysis = analyze_brand(doc, raw_html)
    off_brand = analysis.colors_found - allowed

    if not off_brand:
        return [], 0.0

    deduction_each = _brand_param(config, "deduction_off_brand_color", 0.20)
    cap = int(_brand_param(config, "max_color_issues_reported", 10))
    issues: list[str] = []
    for color in sorted(off_brand):
        if len(issues) < cap:
            issues.append(f"Off-brand color: {color}")

    return issues, deduction_each * len(off_brand)


def brand_font_compliance(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check font-family declarations against approved brand fonts."""
    required_raw: list[str] = config.params.get("required_fonts", []) if config else []
    if not required_raw:
        return [], 0.0

    approved = {f.strip().lower() for f in required_raw}

    analysis = analyze_brand(doc, raw_html)
    non_brand = analysis.fonts_found - approved - _GENERIC_FONTS

    if not non_brand:
        return [], 0.0

    deduction_each = _brand_param(config, "deduction_wrong_font", 0.15)
    cap = int(_brand_param(config, "max_font_issues_reported", 5))
    issues: list[str] = []
    for font in sorted(non_brand):
        if len(issues) < cap:
            issues.append(f"Non-brand font: {font}")

    return issues, deduction_each * len(non_brand)


def brand_required_footer(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check footer section is present (if required by brand rules)."""
    required: list[str] = config.params.get("required_elements", []) if config else []
    if "footer" not in required:
        return [], 0.0

    analysis = analyze_brand(doc, raw_html)
    if analysis.has_footer:
        return [], 0.0

    deduction = _brand_param(config, "deduction_missing_footer", 0.25)
    return ["Required footer section missing"], deduction


def brand_required_logo(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check brand logo image is present (if required by brand rules)."""
    required: list[str] = config.params.get("required_elements", []) if config else []
    if "logo" not in required:
        return [], 0.0

    analysis = analyze_brand(doc, raw_html)
    if analysis.has_logo:
        return [], 0.0

    deduction = _brand_param(config, "deduction_missing_logo", 0.25)
    return ["Required brand logo missing"], deduction


def brand_required_unsubscribe(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check unsubscribe link is present (if required by brand rules)."""
    required: list[str] = config.params.get("required_elements", []) if config else []
    if "unsubscribe" not in required:
        return [], 0.0

    analysis = analyze_brand(doc, raw_html)
    if analysis.has_unsubscribe:
        return [], 0.0

    deduction = _brand_param(config, "deduction_missing_unsubscribe", 0.25)
    return ["Required unsubscribe link missing"], deduction


def brand_forbidden_patterns(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check for forbidden text patterns in email content."""
    patterns_raw: list[str] = config.params.get("forbidden_patterns", []) if config else []
    if not patterns_raw:
        return [], 0.0

    analysis = analyze_brand(doc, raw_html)
    text_lower = analysis.raw_text.lower()

    deduction_each = _brand_param(config, "deduction_forbidden_pattern", 0.20)
    cap = int(_brand_param(config, "max_pattern_issues_reported", 5))
    issues: list[str] = []
    total = 0.0

    for pattern in patterns_raw:
        try:
            if re.search(re.escape(pattern.lower()), text_lower):
                if len(issues) < cap:
                    issues.append(f'Forbidden pattern found: "{pattern}"')
                total += deduction_each
        except re.error:
            continue

    return issues, total


def brand_compliance_summary(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Informational brand compliance summary — no deduction."""
    analysis = analyze_brand(doc, raw_html)
    parts: list[str] = [
        f"Brand compliance: {len(analysis.colors_found)} colors, "
        f"{len(analysis.fonts_found)} fonts found; "
        f"footer={'yes' if analysis.has_footer else 'no'}, "
        f"logo={'yes' if analysis.has_logo else 'no'}, "
        f"unsubscribe={'yes' if analysis.has_unsubscribe else 'no'}"
    ]
    return parts, 0.0


# Register brand compliance custom checks
register_custom_check("brand_color_compliance", brand_color_compliance)
register_custom_check("brand_font_compliance", brand_font_compliance)
register_custom_check("brand_required_footer", brand_required_footer)
register_custom_check("brand_required_logo", brand_required_logo)
register_custom_check("brand_required_unsubscribe", brand_required_unsubscribe)
register_custom_check("brand_forbidden_patterns", brand_forbidden_patterns)
register_custom_check("brand_compliance_summary", brand_compliance_summary)


# ---------------------------------------------------------------------------
# Image Optimization check functions
# ---------------------------------------------------------------------------

from app.qa_engine.image_analyzer import BANNED_FORMATS  # noqa: E402
from app.qa_engine.image_analyzer import get_cached_result as get_img_cached_result  # noqa: E402


def _img_param(config: QACheckConfig | None, key: str, default: float) -> float:
    """Resolve image optimization config parameter."""
    if config and key in config.params:
        return float(config.params[key])
    return default


def image_missing_dimensions(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag images missing width and/or height attributes (excluding tracking pixels)."""
    result = get_img_cached_result(raw_html)
    deduction = _img_param(config, "deduction_missing_dimensions", 0.05)
    cap = int(_img_param(config, "max_dimension_issues_reported", 5))
    issues: list[str] = []
    count = 0
    for img in result.images:
        if img.is_tracking_pixel:
            continue
        if img.width is None or img.height is None:
            count += 1
            if len(issues) < cap:
                missing: list[str] = []
                if img.width is None:
                    missing.append("width")
                if img.height is None:
                    missing.append("height")
                src_display = img.src[:60] + "..." if len(img.src) > 60 else img.src
                issues.append(f"Image missing {', '.join(missing)}: {src_display}")
    if count > cap:
        issues.append(f"... and {count - cap} more images with missing dimensions")
    return issues, round(count * deduction, 4)


def image_missing_alt(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag non-decorative images missing alt attribute entirely."""
    result = get_img_cached_result(raw_html)
    deduction = _img_param(config, "deduction_missing_alt", 0.05)
    cap = int(_img_param(config, "max_alt_issues_reported", 5))
    issues: list[str] = []
    count = 0
    for img in result.images:
        if img.is_tracking_pixel:
            continue
        if img.alt is None:  # None = attribute absent (not empty string)
            count += 1
            if len(issues) < cap:
                src_display = img.src[:60] + "..." if len(img.src) > 60 else img.src
                issues.append(f"Image missing alt attribute: {src_display}")
    if count > cap:
        issues.append(f"... and {count - cap} more images without alt")
    return issues, round(count * deduction, 4)


def image_empty_src(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag images with empty or missing src."""
    result = get_img_cached_result(raw_html)
    deduction = _img_param(config, "deduction_empty_src", 0.10)
    cap = int(_img_param(config, "max_src_issues_reported", 3))
    issues: list[str] = []
    count = 0
    for img in result.images:
        if not img.src:
            count += 1
            if len(issues) < cap:
                issues.append("Image with empty or missing src attribute")
    if count > cap:
        issues.append(f"... and {count - cap} more images with empty src")
    return issues, round(count * deduction, 4)


def image_banned_format(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag BMP/TIFF images."""
    result = get_img_cached_result(raw_html)
    deduction = _img_param(config, "deduction_banned_format", 0.10)
    cap = int(_img_param(config, "max_format_issues_reported", 3))
    issues: list[str] = []
    count = 0
    for img in result.images:
        if img.format in BANNED_FORMATS:
            count += 1
            if len(issues) < cap:
                src_display = img.src[:60] + "..." if len(img.src) > 60 else img.src
                issues.append(f"{img.format.value.upper()} format: {src_display}")
    if count > cap:
        issues.append(f"... and {count - cap} more banned format images")
    return issues, round(count * deduction, 4)


def image_data_uri_oversize(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag data URIs exceeding size threshold."""
    result = get_img_cached_result(raw_html)
    deduction = _img_param(config, "deduction_data_uri_oversize", 0.10)
    threshold = int(_img_param(config, "data_uri_max_bytes", 3072))  # 3KB
    cap = int(_img_param(config, "max_data_uri_issues_reported", 3))
    issues: list[str] = []
    count = 0
    for img in result.images:
        if img.is_data_uri and img.data_uri_bytes > threshold:
            count += 1
            if len(issues) < cap:
                kb = round(img.data_uri_bytes / 1024, 1)
                issues.append(f"Data URI image {kb}KB exceeds {threshold // 1024}KB threshold")
    if count > cap:
        issues.append(f"... and {count - cap} more oversized data URI images")
    return issues, round(count * deduction, 4)


def image_invalid_dimension_value(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag non-numeric dimension values (e.g., '100px', 'auto')."""
    result = get_img_cached_result(raw_html)
    deduction = _img_param(config, "deduction_invalid_dimension", 0.03)
    cap = int(_img_param(config, "max_dimension_issues_reported", 5))
    issues: list[str] = []
    count = 0
    for img in result.images:
        for attr_name, attr_val in [("width", img.width), ("height", img.height)]:
            if attr_val is not None:
                stripped = attr_val.strip()
                if stripped and not stripped.isdigit():
                    count += 1
                    if len(issues) < cap:
                        src_display = img.src[:50] + "..." if len(img.src) > 50 else img.src
                        issues.append(f'Invalid {attr_name}="{attr_val}" on: {src_display}')
    if count > cap:
        issues.append(f"... and {count - cap} more invalid dimension values")
    return issues, round(count * deduction, 4)


def image_tracking_pixel_visible(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag tracking pixels that are visible to screen readers."""
    result = get_img_cached_result(raw_html)
    deduction = _img_param(config, "deduction_tracking_pixel", 0.03)
    cap = int(_img_param(config, "max_tracking_issues_reported", 3))
    issues: list[str] = []
    count = 0
    for img in result.images:
        if not img.is_tracking_pixel:
            continue
        problems: list[str] = []
        if img.alt is None or img.alt != "":
            problems.append('needs alt=""')
        if not img.has_aria_hidden:
            problems.append('needs aria-hidden="true"')
        if problems:
            count += 1
            if len(issues) < cap:
                src_display = img.src[:50] + "..." if len(img.src) > 50 else img.src
                issues.append(f"Tracking pixel ({', '.join(problems)}): {src_display}")
    if count > cap:
        issues.append(f"... and {count - cap} more tracking pixel issues")
    return issues, round(count * deduction, 4)


def image_missing_border_zero(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag images inside <a> tags without border='0'."""
    result = get_img_cached_result(raw_html)
    deduction = _img_param(config, "deduction_missing_border", 0.03)
    cap = int(_img_param(config, "max_border_issues_reported", 5))
    issues: list[str] = []
    count = 0
    for img in result.images:
        if img.is_inside_link and not img.has_border_zero:
            count += 1
            if len(issues) < cap:
                src_display = img.src[:60] + "..." if len(img.src) > 60 else img.src
                issues.append(f"Linked image without border='0': {src_display}")
    if count > cap:
        issues.append(f"... and {count - cap} more images without border='0'")
    return issues, round(count * deduction, 4)


def image_missing_display_block(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag images without display:block in inline style."""
    result = get_img_cached_result(raw_html)
    deduction = _img_param(config, "deduction_missing_display_block", 0.02)
    cap = int(_img_param(config, "max_display_issues_reported", 5))
    issues: list[str] = []
    count = 0
    for img in result.images:
        if img.is_tracking_pixel:
            continue
        if not img.has_display_block:
            count += 1
            if len(issues) < cap:
                src_display = img.src[:60] + "..." if len(img.src) > 60 else img.src
                issues.append(f"Image without display:block: {src_display}")
    if count > cap:
        issues.append(f"... and {count - cap} more images without display:block")
    return issues, round(count * deduction, 4)


def image_summary(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Informational summary of image analysis."""
    result = get_img_cached_result(raw_html)
    if result.total_count == 0:
        return ["Images: none found"], 0.0

    parts = [f"Images: {result.total_count} total"]
    if result.tracking_pixel_count:
        parts.append(f"{result.tracking_pixel_count} tracking pixel(s)")
    if result.format_distribution:
        fmt_str = ", ".join(f"{k}: {v}" for k, v in sorted(result.format_distribution.items()))
        parts.append(f"formats: {fmt_str}")
    parts.append(f"{result.images_with_alt}/{result.total_count} with alt text")
    return ["; ".join(parts)], 0.0


# Register image optimization custom checks
register_custom_check("image_missing_dimensions", image_missing_dimensions)
register_custom_check("image_missing_alt", image_missing_alt)
register_custom_check("image_empty_src", image_empty_src)
register_custom_check("image_banned_format", image_banned_format)
register_custom_check("image_data_uri_oversize", image_data_uri_oversize)
register_custom_check("image_invalid_dimension_value", image_invalid_dimension_value)
register_custom_check("image_tracking_pixel_visible", image_tracking_pixel_visible)
register_custom_check("image_missing_border_zero", image_missing_border_zero)
register_custom_check("image_missing_display_block", image_missing_display_block)
register_custom_check("image_summary", image_summary)


# ---------------------------------------------------------------------------
# CSS Syntax Validation check functions
# ---------------------------------------------------------------------------

import logging as _stdlib_logging  # noqa: E402

import cssutils  # noqa: E402

# Silence cssutils logging (it logs parse errors to stderr by default)
cssutils.log.setLevel(_stdlib_logging.CRITICAL)  # pyright: ignore[reportUnknownMemberType,reportArgumentType]

_VENDOR_PREFIX_RE = re.compile(r"-(?:webkit|moz|ms|o)-[\w-]+")
_IMPORTANT_RE = re.compile(r"!important", re.IGNORECASE)
_IMPORT_RE = re.compile(r"@import\s", re.IGNORECASE)
_STYLE_BLOCK_RE_CSS = re.compile(r"<style[^>]*>(.*?)</style>", re.DOTALL | re.IGNORECASE)
_INLINE_STYLE_RE_CSS = re.compile(r"style\s*=\s*(?:\"([^\"]*)\"|'([^']*)')", re.IGNORECASE)
_LINK_STYLESHEET_RE = re.compile(r"<link[^>]+rel\s*=\s*[\"']stylesheet[\"'][^>]*>", re.IGNORECASE)
_EMPTY_DECL_RE = re.compile(r"([\w-]+)\s*:\s*;")
# Layout-critical properties that MUST be inlined for Gmail
_LAYOUT_CRITICAL_PROPS = frozenset(
    {
        "display",
        "width",
        "max-width",
        "min-width",
        "height",
        "float",
        "position",
        "margin",
        "padding",
        "text-align",
        "vertical-align",
        "background-color",
        "color",
        "font-size",
        "font-family",
        "line-height",
        "border",
    }
)


def _css_param(config: QACheckConfig | None, key: str, default: float) -> float:
    """Resolve a CSS syntax check parameter from config."""
    if config and key in config.params:
        return float(config.params[key])
    return default


def _parse_css_blocks(html: str) -> list[str]:
    """Extract CSS content from <style> blocks."""
    return [m.group(1) for m in _STYLE_BLOCK_RE_CSS.finditer(html)]


def _parse_inline_styles(html: str) -> list[str]:
    """Extract inline style values from both double- and single-quoted attributes."""
    return [m.group(1) or m.group(2) for m in _INLINE_STYLE_RE_CSS.finditer(html)]


def css_syntax_errors(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect CSS syntax errors using cssutils parser."""
    blocks = _parse_css_blocks(raw_html)
    if not blocks:
        return [], 0.0

    max_reported = int(_css_param(config, "max_syntax_errors_reported", 5))
    deduction = _css_param(config, "deduction_syntax_error", 0.15)

    all_errors: list[str] = []
    for block in blocks:
        sheet = cssutils.parseString(block, validate=True)  # pyright: ignore[reportUnknownMemberType]  # type: ignore[no-untyped-call]
        for rule in sheet:
            if rule.type == rule.UNKNOWN_RULE:
                all_errors.append(f"Unknown CSS rule: {rule.cssText[:60]}")

    if not all_errors:
        return [], 0.0

    issues = all_errors[:max_reported]
    if len(all_errors) > max_reported:
        issues.append(f"... and {len(all_errors) - max_reported} more syntax errors")

    return issues, deduction


def css_empty_declarations(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect empty CSS declarations (property: ;)."""
    max_reported = int(_css_param(config, "max_empty_declarations_reported", 5))
    deduction = _css_param(config, "deduction_empty_declaration", 0.05)

    all_css = _parse_css_blocks(raw_html) + _parse_inline_styles(raw_html)
    issues: list[str] = []

    for css in all_css:
        for m in _EMPTY_DECL_RE.finditer(css):
            issues.append(f"Empty declaration: '{m.group(1)}: ;'")

    if not issues:
        return [], 0.0

    reported = issues[:max_reported]
    if len(issues) > max_reported:
        reported.append(f"... and {len(issues) - max_reported} more")

    return reported, deduction


def css_vendor_prefixes(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect vendor-prefixed CSS properties (useless in email)."""
    max_reported = int(_css_param(config, "max_vendor_prefixes_reported", 5))
    deduction = _css_param(config, "deduction_vendor_prefix", 0.05)

    all_css = "\n".join(_parse_css_blocks(raw_html) + _parse_inline_styles(raw_html))
    matches = _VENDOR_PREFIX_RE.findall(all_css)

    if not matches:
        return [], 0.0

    unique = sorted(set(matches))
    issues = [f"Vendor prefix: '{p}' (ignored by email clients)" for p in unique[:max_reported]]
    if len(unique) > max_reported:
        issues.append(f"... and {len(unique) - max_reported} more vendor prefixes")

    return issues, deduction


def css_external_stylesheet(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect <link rel='stylesheet'> tags (stripped by all email clients)."""
    deduction = _css_param(config, "deduction_external_stylesheet", 0.25)

    matches = _LINK_STYLESHEET_RE.findall(raw_html)
    if not matches:
        return [], 0.0

    issues = [f"External stylesheet detected: {m[:80]}" for m in matches]
    return issues, deduction


def css_import_rule(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect @import rules (stripped by Gmail and most clients)."""
    deduction = _css_param(config, "deduction_import_rule", 0.20)

    blocks = _parse_css_blocks(raw_html)
    issues: list[str] = []
    for block in blocks:
        for m in _IMPORT_RE.finditer(block):
            line_start = block.rfind("\n", 0, m.start()) + 1
            line_end = block.find(";", m.start())
            if line_end == -1:
                line_end = block.find("\n", m.start())
            if line_end == -1:
                line_end = len(block)
            line = block[line_start : line_end + 1].strip()
            issues.append(f"@import rule: {line[:80]}")

    if not issues:
        return [], 0.0

    return issues, deduction


def css_important_overuse(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect excessive !important usage (may conflict with dark mode)."""
    threshold = int(_css_param(config, "important_threshold", 10))
    deduction = _css_param(config, "deduction_important_overuse", 0.10)

    all_css = "\n".join(_parse_css_blocks(raw_html) + _parse_inline_styles(raw_html))
    count = len(_IMPORTANT_RE.findall(all_css))

    if count <= threshold:
        return [], 0.0

    # Don't count !important inside dark mode media queries (those are expected).
    # Use brace-balancing to extract content of dark mode blocks, supporting
    # multi-condition queries like @media (min-width: 600px) and (prefers-color-scheme: dark).
    dark_mode_count = 0
    dark_media_start_re = re.compile(
        r"@media\s[^{]*prefers-color-scheme\s*:\s*dark[^{]*\{",
        re.IGNORECASE,
    )
    for block in _parse_css_blocks(raw_html):
        for dm_match in dark_media_start_re.finditer(block):
            # Walk forward from opening brace, balancing braces to find the end
            start = dm_match.end()
            depth = 1
            pos = start
            while pos < len(block) and depth > 0:
                if block[pos] == "{":
                    depth += 1
                elif block[pos] == "}":
                    depth -= 1
                pos += 1
            dark_content = block[start : pos - 1]
            dark_mode_count += len(_IMPORTANT_RE.findall(dark_content))
    non_dark_count = count - dark_mode_count

    if non_dark_count <= threshold:
        return [], 0.0

    issues = [
        f"{non_dark_count} !important declarations outside dark mode "
        f"(threshold: {threshold}) — may conflict with client dark mode injection"
    ]
    return issues, deduction


def css_non_inline_dependency(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect layout-critical CSS in <style> blocks without inline fallbacks."""
    max_reported = int(_css_param(config, "max_non_inline_reported", 5))
    deduction = _css_param(config, "deduction_non_inline", 0.10)

    style_blocks = _parse_css_blocks(raw_html)
    if not style_blocks:
        return [], 0.0

    all_block_css = "\n".join(style_blocks)
    inline_styles = _parse_inline_styles(raw_html)
    issues: list[str] = []

    for prop in sorted(_LAYOUT_CRITICAL_PROPS):
        # Use word boundary (or start-of-line/semicolon) to prevent partial matches
        # e.g. "color" must not match "background-color"
        prop_pattern = rf"(?<![a-zA-Z-]){re.escape(prop)}\s*:"
        prop_in_block = re.search(prop_pattern, all_block_css, re.IGNORECASE)
        if prop_in_block:
            prop_inline = any(
                re.search(prop_pattern, style, re.IGNORECASE) for style in inline_styles
            )
            if not prop_inline:
                issues.append(f"'{prop}' in <style> block only — no inline fallback for Gmail")

    if not issues:
        return [], 0.0

    reported = issues[:max_reported]
    if len(issues) > max_reported:
        reported.append(f"... and {len(issues) - max_reported} more")

    return reported, deduction


def css_syntax_summary(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Informational summary of CSS syntax validation."""
    blocks = _parse_css_blocks(raw_html)
    inline = _parse_inline_styles(raw_html)
    all_css = "\n".join(blocks + inline)

    vendor_count = len(set(_VENDOR_PREFIX_RE.findall(all_css)))
    important_count = len(_IMPORTANT_RE.findall(all_css))
    external_count = len(_LINK_STYLESHEET_RE.findall(raw_html))
    import_count = len(_IMPORT_RE.findall(all_css))

    parts: list[str] = []
    if vendor_count:
        parts.append(f"{vendor_count} vendor prefixes")
    if important_count:
        parts.append(f"{important_count} !important")
    if external_count:
        parts.append(f"{external_count} external stylesheets")
    if import_count:
        parts.append(f"{import_count} @import rules")

    summary = f"CSS audit: {len(blocks)} style blocks, {len(inline)} inline styles"
    if parts:
        summary += f" — {', '.join(parts)}"

    return [summary], 0.0


# Register CSS syntax validation custom checks
register_custom_check("css_syntax_errors", css_syntax_errors)
register_custom_check("css_empty_declarations", css_empty_declarations)
register_custom_check("css_vendor_prefixes", css_vendor_prefixes)
register_custom_check("css_external_stylesheet", css_external_stylesheet)
register_custom_check("css_import_rule", css_import_rule)
register_custom_check("css_important_overuse", css_important_overuse)
register_custom_check("css_non_inline_dependency", css_non_inline_dependency)
register_custom_check("css_syntax_summary", css_syntax_summary)


# ---------------------------------------------------------------------------
# Personalisation Syntax Validation check functions
# ---------------------------------------------------------------------------

from app.qa_engine.personalisation_validator import (  # noqa: E402
    ESPPlatform,
    analyze_personalisation,
)


def _ps_param(config: QACheckConfig | None, key: str, default: float) -> float:
    """Resolve personalisation config parameter."""
    if config and key in config.params:
        return float(config.params[key])
    return default


def personalisation_mixed_platform(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect if multiple ESP platforms are used in same template."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    if analysis.is_mixed_platform:
        deduction = _ps_param(config, "deduction_mixed_platform", 0.30)
        platforms = ", ".join(p.value for p in analysis.detected_platforms)
        return [f"Mixed platforms detected: {platforms}"], deduction
    return [], 0.0


def personalisation_unknown_platform(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag when personalisation tags exist but platform can't be identified."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    if analysis.primary_platform == ESPPlatform.UNKNOWN:
        deduction = _ps_param(config, "deduction_unknown_platform", 0.10)
        return ["Personalisation tags detected but ESP platform could not be identified"], deduction
    return [], 0.0


def personalisation_delimiter_balance(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check all personalisation delimiters are properly balanced."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    errors = analysis.unbalanced_delimiters
    if not errors:
        return [], 0.0
    deduction = _ps_param(config, "deduction_delimiter_unbalanced", 0.15)
    cap = int(_ps_param(config, "max_delimiter_issues", 5))
    issues = errors[:cap]
    if len(errors) > cap:
        issues.append(f"... and {len(errors) - cap} more delimiter issues")
    return issues, round(len(errors) * deduction, 4)


def personalisation_conditional_balance(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check conditional blocks (if/endif, IF/ENDIF, etc.) are balanced."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    errors = analysis.unbalanced_conditionals
    if not errors:
        return [], 0.0
    deduction = _ps_param(config, "deduction_conditional_unbalanced", 0.15)
    cap = int(_ps_param(config, "max_conditional_issues", 5))
    issues = errors[:cap]
    if len(errors) > cap:
        issues.append(f"... and {len(errors) - cap} more conditional issues")
    return issues, round(len(errors) * deduction, 4)


def personalisation_fallback_missing(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag output tags without fallback values."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    # Find output tags without fallbacks
    missing = [t for t in analysis.tags if t.tag_type == "output" and not t.has_fallback]
    if not missing:
        return [], 0.0
    deduction = _ps_param(config, "deduction_fallback_missing", 0.05)
    cap = int(_ps_param(config, "max_fallback_issues", 10))
    issues: list[str] = []
    for t in missing[:cap]:
        var = t.variable_name or t.raw[:40]
        issues.append(f"No fallback for '{var}' at line {t.line_number}")
    if len(missing) > cap:
        issues.append(f"... and {len(missing) - cap} more tags without fallbacks")
    return issues, round(len(missing) * deduction, 4)


def personalisation_fallback_empty(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag fallbacks that resolve to empty string."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    errors = analysis.empty_fallbacks
    if not errors:
        return [], 0.0
    deduction = _ps_param(config, "deduction_fallback_empty", 0.03)
    cap = int(_ps_param(config, "max_fallback_empty_issues", 5))
    issues = errors[:cap]
    if len(errors) > cap:
        issues.append(f"... and {len(errors) - cap} more empty fallbacks")
    return issues, round(len(errors) * deduction, 4)


def personalisation_liquid_syntax(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Validate Liquid syntax for Braze/Klaviyo templates."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    if analysis.primary_platform not in (ESPPlatform.BRAZE, ESPPlatform.KLAVIYO):
        return [], 0.0
    errors = analysis.syntax_errors
    if not errors:
        return [], 0.0
    deduction = _ps_param(config, "deduction_syntax_error", 0.10)
    cap = int(_ps_param(config, "max_syntax_issues", 5))
    issues = errors[:cap]
    if len(errors) > cap:
        issues.append(f"... and {len(errors) - cap} more syntax errors")
    return issues, round(len(errors) * deduction, 4)


def personalisation_ampscript_syntax(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Validate AMPscript syntax for SFMC templates."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    if analysis.primary_platform != ESPPlatform.SFMC:
        return [], 0.0
    errors = analysis.syntax_errors
    if not errors:
        return [], 0.0
    deduction = _ps_param(config, "deduction_syntax_error", 0.10)
    cap = int(_ps_param(config, "max_syntax_issues", 5))
    issues = errors[:cap]
    if len(errors) > cap:
        issues.append(f"... and {len(errors) - cap} more syntax errors")
    return issues, round(len(errors) * deduction, 4)


def personalisation_jssp_syntax(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Validate JSSP/EL syntax for Adobe Campaign templates."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    if analysis.primary_platform != ESPPlatform.ADOBE_CAMPAIGN:
        return [], 0.0
    errors = analysis.syntax_errors
    if not errors:
        return [], 0.0
    deduction = _ps_param(config, "deduction_syntax_error", 0.10)
    cap = int(_ps_param(config, "max_syntax_issues", 5))
    issues = errors[:cap]
    if len(errors) > cap:
        issues.append(f"... and {len(errors) - cap} more syntax errors")
    return issues, round(len(errors) * deduction, 4)


def personalisation_other_syntax(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Validate syntax for Mailchimp/HubSpot/Iterable templates."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    if analysis.primary_platform not in (
        ESPPlatform.MAILCHIMP,
        ESPPlatform.HUBSPOT,
        ESPPlatform.ITERABLE,
    ):
        return [], 0.0
    errors = analysis.syntax_errors
    if not errors:
        return [], 0.0
    deduction = _ps_param(config, "deduction_syntax_error", 0.10)
    cap = int(_ps_param(config, "max_syntax_issues", 5))
    issues = errors[:cap]
    if len(errors) > cap:
        issues.append(f"... and {len(errors) - cap} more syntax errors")
    return issues, round(len(errors) * deduction, 4)


def personalisation_nesting_depth(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag excessive conditional nesting (>3 levels)."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return [], 0.0
    errors = analysis.nested_depth_violations
    if not errors:
        return [], 0.0
    deduction = _ps_param(config, "deduction_nesting_depth", 0.03)
    cap = int(_ps_param(config, "max_nesting_issues", 3))
    issues = errors[:cap]
    if len(errors) > cap:
        issues.append(f"... and {len(errors) - cap} more nesting violations")
    return issues, round(len(errors) * deduction, 4)


def personalisation_summary_stats(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Informational summary — no deduction."""
    analysis = analyze_personalisation(raw_html)
    if not analysis.has_personalisation:
        return ["Summary: No personalisation tags found"], 0.0

    platform = analysis.primary_platform.value
    parts = [f"Summary: {analysis.total_tags} tag(s), platform: {platform}"]
    if analysis.tags_with_fallback:
        parts.append(f"{analysis.tags_with_fallback} with fallback")
    if analysis.tags_without_fallback:
        parts.append(f"{analysis.tags_without_fallback} without fallback")
    return [", ".join(parts)], 0.0


# Register personalisation syntax custom checks
register_custom_check("personalisation_mixed_platform", personalisation_mixed_platform)
register_custom_check("personalisation_unknown_platform", personalisation_unknown_platform)
register_custom_check("personalisation_delimiter_balance", personalisation_delimiter_balance)
register_custom_check("personalisation_conditional_balance", personalisation_conditional_balance)
register_custom_check("personalisation_fallback_missing", personalisation_fallback_missing)
register_custom_check("personalisation_fallback_empty", personalisation_fallback_empty)
register_custom_check("personalisation_liquid_syntax", personalisation_liquid_syntax)
register_custom_check("personalisation_ampscript_syntax", personalisation_ampscript_syntax)
register_custom_check("personalisation_jssp_syntax", personalisation_jssp_syntax)
register_custom_check("personalisation_other_syntax", personalisation_other_syntax)
register_custom_check("personalisation_nesting_depth", personalisation_nesting_depth)
register_custom_check("personalisation_summary_stats", personalisation_summary_stats)
