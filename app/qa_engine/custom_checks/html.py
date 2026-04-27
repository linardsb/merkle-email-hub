# ruff: noqa: ARG001
"""HTML structure custom checks (domain split from custom_checks.py).

Each function follows the CustomCheckFn protocol:
    (doc, raw_html, config) -> (issues: list[str], deduction: float)
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
